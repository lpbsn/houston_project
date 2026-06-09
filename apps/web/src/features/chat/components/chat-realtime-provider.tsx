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

import { chatQueryKeys, markConversationSeen } from '../api'
import {
  useAppendChatMessageToCache,
  useChatConversationsQuery,
  useChatStatusQuery,
} from '../hooks'
import { useChatWebSocket } from '../hooks/use-chat-websocket'
import type {
  ChatConnectionStatus,
  ChatWsAccessRevokedEvent,
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
  showChatNav: boolean
  hasUnread: boolean
}

const ChatRealtimeContext = createContext<ChatRealtimeContextValue | null>(null)

type ChatRealtimeProviderProps = PropsWithChildren<{
  establishmentId: string | null
  activeConversationId?: string | null
  onAccessRevoked?: (event: ChatWsAccessRevokedEvent) => void
}>

function createClientMessageId(): string {
  return crypto.randomUUID()
}

export function ChatRealtimeProvider({
  establishmentId,
  activeConversationId = null,
  onAccessRevoked,
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
          ? { ...message, status: 'failed' }
          : message,
      ),
    )
  }, [])

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

        return queued ? { ...message, status: 'pending' } : message
      }),
    )
  }, [activeConversationId, establishmentId, queryClient])

  const { connectionStatus, sendMessage, reconnect } = useChatWebSocket({
    establishmentId,
    enabled: chatEnabled,
    onMessageCreated: handleMessageCreated,
    onMessageRejected: handleMessageRejected,
    onAccessRevoked,
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
          item.clientMessageId === clientMessageId ? { ...item, status: 'pending' } : item,
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
            item.clientMessageId === clientMessageId ? { ...item, status: 'failed' } : item,
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
      showChatNav: chatEnabled,
      hasUnread,
    }),
    [chatEnabled, connectionStatus, hasUnread, localMessages, retryFailedMessage, sendChatMessage],
  )

  return (
    <ChatRealtimeContext.Provider value={value}>{children}</ChatRealtimeContext.Provider>
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
