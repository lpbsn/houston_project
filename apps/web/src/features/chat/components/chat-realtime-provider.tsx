import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type PropsWithChildren,
} from 'react'
import { useQueryClient } from '@tanstack/react-query'

import { useAuth } from '@/app/auth-provider'
import { LegalConsentSheet } from '@/features/auth/components/legal-consent-sheet'
import { isTermsAcceptanceRequired } from '@/lib/legal'

import { chatQueryKeys, markConversationSeen } from '../api'
import {
  useAppendChatMessageToCache,
  useChatConversationsQuery,
  useChatStatusQuery,
} from '../hooks'
import { useChatWebSocket } from '../hooks/use-chat-websocket'
import {
  asPendingLocalChatMessage,
  selectLocalMessagesToRetryAfterTermsAccept,
} from '../lib/chat-terms-retry'
import { purgeConversationClientState } from '../lib/purge-conversation-client-state'
import type {
  ChatConnectionStatus,
  ChatWsConversationAccessRevokedEvent,
  ChatWsConversationUpdatedEvent,
  ChatWsGlobalAccessRevokedEvent,
  ChatWsMessageCreatedEvent,
  ChatWsMessageRejectedEvent,
  LocalChatMessage,
} from '../types'

type ChatRealtimeContextValue = {
  connectionStatus: ChatConnectionStatus
  localMessages: LocalChatMessage[]
  sendChatMessage: (payload: {
    conversationId: string
    body: string
    authorMembershipId: string
    authorDisplayName: string
  }) => { clientMessageId: string; queued: boolean }
  retryFailedMessage: (clientMessageId: string) => boolean
  clearLocalMessagesForConversation: (conversationId: string) => void
  showChatNav: boolean
  hasUnread: boolean
}

const ChatRealtimeContext = createContext<ChatRealtimeContextValue | null>(null)

type ChatRealtimeProviderProps = PropsWithChildren<{
  establishmentId: string | null
  activeConversationId?: string | null
  onGlobalAccessRevoked?: (event: ChatWsGlobalAccessRevokedEvent) => void
  onConversationAccessRevoked?: (event: ChatWsConversationAccessRevokedEvent) => void
}>

function createClientMessageId(): string {
  return crypto.randomUUID()
}

export function ChatRealtimeProvider({
  establishmentId,
  activeConversationId = null,
  onGlobalAccessRevoked,
  onConversationAccessRevoked,
  children,
}: ChatRealtimeProviderProps) {
  const auth = useAuth()
  const viewerMembershipId = auth.bootstrap?.active_membership?.id ?? null
  const queryClient = useQueryClient()
  const appendMessageToCache = useAppendChatMessageToCache()
  const statusQuery = useChatStatusQuery(establishmentId)
  const conversationsQuery = useChatConversationsQuery(establishmentId, {
    enabled: Boolean(statusQuery.data?.can_access),
  })
  const [localMessages, setLocalMessages] = useState<LocalChatMessage[]>([])
  const [legalKind, setLegalKind] = useState<'terms' | null>(null)
  const sendMessageRef = useRef<
    (payload: { conversationId: string; clientMessageId: string; body: string }) => boolean
  >(() => false)

  const chatEnabled = Boolean(statusQuery.data?.can_access && statusQuery.data.chat_enabled)
  const hasUnread = (conversationsQuery.data?.items ?? []).some((item) => item.unread)

  const handleMessageCreated = useCallback(
    (event: ChatWsMessageCreatedEvent) => {
      if (!establishmentId) {
        return
      }

      appendMessageToCache(establishmentId, event.conversation_id, event.message, {
        viewerMembershipId,
        activeConversationId,
      })

      if (
        activeConversationId &&
        event.conversation_id === activeConversationId &&
        viewerMembershipId &&
        event.message.author_membership_id !== viewerMembershipId
      ) {
        void markConversationSeen(establishmentId, activeConversationId).catch(() => undefined)
      }

      setLocalMessages((current) =>
        current.filter((message) => message.clientMessageId !== event.message.client_message_id),
      )
    },
    [
      activeConversationId,
      appendMessageToCache,
      establishmentId,
      viewerMembershipId,
    ],
  )

  const handleMessageRejected = useCallback((event: ChatWsMessageRejectedEvent) => {
    if (!event.client_message_id) {
      return
    }

    setLocalMessages((current) =>
      current.map((message) =>
        message.clientMessageId === event.client_message_id
          ? { ...message, status: 'failed', rejectCode: event.code }
          : message,
      ),
    )

    if (isTermsAcceptanceRequired({ code: event.code })) {
      setLegalKind('terms')
    }
  }, [])

  const handleTermsAccepted = useCallback(() => {
    setLocalMessages((current) => {
      const retryIds = new Set(
        selectLocalMessagesToRetryAfterTermsAccept(current).map(
          (message) => message.clientMessageId,
        ),
      )

      return current.map((message) => {
        if (!retryIds.has(message.clientMessageId)) {
          return message
        }

        const queued = sendMessageRef.current({
          conversationId: message.conversationId,
          clientMessageId: message.clientMessageId,
          body: message.body,
        })

        return queued ? asPendingLocalChatMessage(message) : { ...message, status: 'failed' }
      })
    })
  }, [])

  const clearLocalMessagesForConversation = useCallback((conversationId: string) => {
    setLocalMessages((current) =>
      current.filter((message) => message.conversationId !== conversationId),
    )
  }, [])

  const handleConversationAccessRevoked = useCallback(
    (event: ChatWsConversationAccessRevokedEvent) => {
      if (establishmentId) {
        purgeConversationClientState(queryClient, {
          establishmentId,
          conversationId: event.conversation_id,
          clearLocalMessages: clearLocalMessagesForConversation,
        })
      }
      onConversationAccessRevoked?.(event)
    },
    [
      clearLocalMessagesForConversation,
      establishmentId,
      onConversationAccessRevoked,
      queryClient,
    ],
  )

  const handleConversationUpdated = useCallback(
    (event: ChatWsConversationUpdatedEvent) => {
      if (!establishmentId) {
        return
      }
      void queryClient.invalidateQueries({ queryKey: chatQueryKeys.conversations(establishmentId) })
      void queryClient.invalidateQueries({
        queryKey: chatQueryKeys.conversation(establishmentId, event.conversation_id),
      })
    },
    [establishmentId, queryClient],
  )

  const handleReconnect = useCallback(() => {
    if (!establishmentId) {
      return
    }

    void queryClient.invalidateQueries({ queryKey: chatQueryKeys.conversations(establishmentId) })
    if (activeConversationId) {
      void queryClient.invalidateQueries({
        queryKey: chatQueryKeys.messages(establishmentId, activeConversationId),
      })
    }

    setLocalMessages((current) =>
      current.map((message) => {
        if (message.status !== 'failed') {
          return message
        }

        const queued = sendMessageRef.current({
          conversationId: message.conversationId,
          clientMessageId: message.clientMessageId,
          body: message.body,
        })

        return queued ? asPendingLocalChatMessage(message) : message
      }),
    )
  }, [activeConversationId, establishmentId, queryClient])

  const { connectionStatus, sendMessage, reconnect } = useChatWebSocket({
    establishmentId,
    enabled: chatEnabled,
    onMessageCreated: handleMessageCreated,
    onMessageRejected: handleMessageRejected,
    onGlobalAccessRevoked,
    onConversationAccessRevoked: handleConversationAccessRevoked,
    onConversationUpdated: handleConversationUpdated,
    onReconnect: handleReconnect,
  })

  useEffect(() => {
    sendMessageRef.current = sendMessage
  }, [sendMessage])

  const sendChatMessage = useCallback(
    (payload: {
      conversationId: string
      body: string
      authorMembershipId: string
      authorDisplayName: string
    }) => {
      const trimmed = payload.body.trim()
      const clientMessageId = createClientMessageId()
      const createdAt = new Date().toISOString()

      const localMessage: LocalChatMessage = {
        clientMessageId,
        conversationId: payload.conversationId,
        body: trimmed,
        status: 'pending',
        createdAt,
        authorMembershipId: payload.authorMembershipId,
        authorDisplayName: payload.authorDisplayName,
      }

      setLocalMessages((current) => [...current, localMessage])

      const queued = sendMessage({
        conversationId: payload.conversationId,
        clientMessageId,
        body: trimmed,
      })

      if (!queued) {
        setLocalMessages((current) =>
          current.map((message) =>
            message.clientMessageId === clientMessageId
              ? { ...message, status: 'failed' }
              : message,
          ),
        )
      }

      return { clientMessageId, queued }
    },
    [sendMessage],
  )

  const retryFailedMessage = useCallback(
    (clientMessageId: string) => {
      const message = localMessages.find((item) => item.clientMessageId === clientMessageId)
      if (!message || message.status !== 'failed') {
        return false
      }

      setLocalMessages((current) =>
        current.map((item) =>
          item.clientMessageId === clientMessageId ? asPendingLocalChatMessage(item) : item,
        ),
      )

      const queued = sendMessage({
        conversationId: message.conversationId,
        clientMessageId: message.clientMessageId,
        body: message.body,
      })

      if (!queued) {
        setLocalMessages((current) =>
          current.map((item) =>
            item.clientMessageId === clientMessageId ? { ...message, status: 'failed' } : item,
          ),
        )
        if (connectionStatus === 'disconnected' || connectionStatus === 'reconnecting') {
          void reconnect()
        }
      }

      return queued
    },
    [connectionStatus, localMessages, reconnect, sendMessage],
  )

  const value = useMemo(
    () => ({
      connectionStatus,
      localMessages,
      sendChatMessage,
      retryFailedMessage,
      clearLocalMessagesForConversation,
      showChatNav: chatEnabled,
      hasUnread,
    }),
    [
      chatEnabled,
      clearLocalMessagesForConversation,
      connectionStatus,
      hasUnread,
      localMessages,
      retryFailedMessage,
      sendChatMessage,
    ],
  )

  return (
    <ChatRealtimeContext.Provider value={value}>
      {children}
      <LegalConsentSheet
        kind={legalKind}
        onClose={() => setLegalKind(null)}
        onAccepted={handleTermsAccepted}
      />
    </ChatRealtimeContext.Provider>
  )
}

export function useChatRealtime() {
  const context = useContext(ChatRealtimeContext)
  if (!context) {
    throw new Error('useChatRealtime must be used within ChatRealtimeProvider.')
  }
  return context
}

export function useOptionalChatRealtime() {
  return useContext(ChatRealtimeContext)
}
