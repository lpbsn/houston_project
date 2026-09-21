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
import { resyncBootstrapAfterLegalError } from '@/features/auth/api'
import { isTermsAcceptanceRequired } from '@/lib/legal'

import {
  ChatApiError,
  chatQueryKeys,
  completeChatUpload,
  markConversationSeen,
  putChatUploadBytes,
  refreshChatUploadPresign,
  reserveChatUpload,
  sendChatMessage as sendChatMessageHttp,
} from '../api'
import {
  useAppendChatMessageToCache,
  useChatConversationsQuery,
  useChatStatusQuery,
} from '../hooks'
import { useChatWebSocket } from '../hooks/use-chat-websocket'
import { asPendingLocalChatMessage } from '../lib/chat-terms-retry'
import {
  clearChatOutbox,
  clearExpiredChatOutboxAttachments,
  loadChatOutboxDrafts,
  persistChatOutboxAttachmentBytes,
  saveChatOutboxDraft,
  type ChatOutboxDraft,
} from '../lib/chat-outbox'
import { dispatchChatOutboxDraft, sendPreparedChatOutboxDraft } from '../lib/chat-send-pipeline'
import { purgeConversationClientState } from '../lib/purge-conversation-client-state'
import type {
  ChatConnectionStatus,
  ChatWsConversationAccessRevokedEvent,
  ChatWsConversationUpdatedEvent,
  ChatWsGlobalAccessRevokedEvent,
  ChatWsMessageCreatedEvent,
  ChatSendMessageResponse,
  ChatWsMessageRejectedEvent,
  LocalChatAttachment,
  LocalChatMessage,
} from '../types'

type SendChatMessagePayload = {
  conversationId: string
  body: string
  mentions?: LocalChatMessage['mentions']
  replyToId?: string | null
  files?: File[]
  authorMembershipId: string
  authorDisplayName: string
  replyPreview?: LocalChatMessage['replyPreview']
}

type ChatRealtimeContextValue = {
  connectionStatus: ChatConnectionStatus
  localMessages: LocalChatMessage[]
  sendChatMessage: (payload: SendChatMessagePayload) => { clientMessageId: string; queued: boolean }
  retryFailedMessage: (clientMessageId: string) => boolean
  cancelSendingMessage: (clientMessageId: string) => boolean
  clearLocalMessagesForConversation: (conversationId: string) => void
  showChatNav: boolean
  hasUnread: boolean
}

const ChatRealtimeContext = createContext<ChatRealtimeContextValue | null>(null)

function createClientMessageId(): string {
  return crypto.randomUUID()
}

function draftToLocalMessage(draft: ChatOutboxDraft): LocalChatMessage {
  return {
    clientMessageId: draft.clientMessageId,
    conversationId: draft.conversationId,
    body: draft.body,
    mentions: draft.mentions,
    replyToId: draft.replyToId,
    attachments: draft.attachments.map((attachment) => ({
      localAttachmentId: attachment.localAttachmentId,
      uploadId: attachment.uploadId,
      filename: attachment.filename,
      contentType: attachment.contentType,
      sizeBytes: attachment.sizeBytes,
      state: attachment.state,
    })),
    status: draft.status,
    createdAt: draft.createdAt,
    authorMembershipId: draft.authorMembershipId,
    authorDisplayName: draft.authorDisplayName,
    rejectCode: draft.rejectCode,
  }
}

export function ChatRealtimeProvider({
  establishmentId,
  activeConversationId = null,
  onGlobalAccessRevoked,
  onConversationAccessRevoked,
  children,
}: PropsWithChildren<{
  establishmentId: string | null
  activeConversationId?: string | null
  onGlobalAccessRevoked?: (event: ChatWsGlobalAccessRevokedEvent) => void
  onConversationAccessRevoked?: (event: ChatWsConversationAccessRevokedEvent) => void
}>) {
  const auth = useAuth()
  const viewerMembershipId = auth.bootstrap?.active_membership?.id ?? null
  const userId = auth.bootstrap?.user.id ?? null
  const queryClient = useQueryClient()
  const appendMessageToCache = useAppendChatMessageToCache()
  const statusQuery = useChatStatusQuery(establishmentId)
  const conversationsQuery = useChatConversationsQuery(establishmentId, {
    enabled: Boolean(statusQuery.data?.can_access),
  })
  const [localMessages, setLocalMessages] = useState<LocalChatMessage[]>([])
  const localMessagesRef = useRef<LocalChatMessage[]>([])
  const inflightRef = useRef(new Set<string>())
  const abortControllersRef = useRef(new Map<string, AbortController>())

  const chatEnabled = Boolean(statusQuery.data?.can_access && statusQuery.data.chat_enabled)
  const hasUnread = (conversationsQuery.data?.items ?? []).some((item) => item.unread)

  useEffect(() => {
    localMessagesRef.current = localMessages
  }, [localMessages])

  const patchLocalMessage = useCallback(
    (clientMessageId: string, updater: (message: LocalChatMessage) => LocalChatMessage) => {
      setLocalMessages((current) =>
        current.map((message) =>
          message.clientMessageId === clientMessageId ? updater(message) : message,
        ),
      )
    },
    [],
  )

  const pipelineDeps = useCallback(
    (conversationEstablishmentId: string) => ({
      reserveUpload: (payload: {
        conversationId: string
        filename: string
        contentType: string
        sizeBytes: number
      }) => reserveChatUpload(conversationEstablishmentId, payload),
      refreshPresign: (uploadId: string) =>
        refreshChatUploadPresign(conversationEstablishmentId, uploadId),
      putBytes: (payload: {
        uploadId: string
        putUrl: string
        blob: Blob
        contentType: string
        signal?: AbortSignal
        onProgress?: (ratio: number) => void
      }) =>
        putChatUploadBytes({
          establishmentId: conversationEstablishmentId,
          ...payload,
        }),
      completeUpload: (uploadId: string) => completeChatUpload(conversationEstablishmentId, uploadId),
      sendMessage: () => {
        throw new Error('sendMessage must be bound to a conversation.')
      },
    }),
    [],
  )

  const failMessage = useCallback(
    async (draft: ChatOutboxDraft, rejectCode?: string) => {
      const stored = (await loadChatOutboxDrafts({ clientMessageId: draft.clientMessageId }))[0]
      const base = stored ?? draft
      const next = { ...base, status: 'failed' as const, rejectCode }
      await saveChatOutboxDraft(next)
      patchLocalMessage(draft.clientMessageId, (message) => ({
        ...message,
        status: 'failed',
        rejectCode,
      }))
      if (isTermsAcceptanceRequired({ code: rejectCode })) {
        void resyncBootstrapAfterLegalError({ code: rejectCode })
      }
    },
    [patchLocalMessage],
  )

  const dispatchDraft = useCallback(
    async (draft: ChatOutboxDraft) => {
      if (inflightRef.current.has(draft.clientMessageId)) {
        return
      }
      inflightRef.current.add(draft.clientMessageId)
      const abortController = new AbortController()
      abortControllersRef.current.set(draft.clientMessageId, abortController)
      const deps = {
        ...pipelineDeps(draft.establishmentId),
        sendMessage: (payload: {
          clientMessageId: string
          body: string
          replyToId?: string | null
          mentions?: ChatOutboxDraft['mentions']
          attachmentIds?: string[]
        }) =>
          sendChatMessageHttp(draft.establishmentId, draft.conversationId, {
            clientMessageId: payload.clientMessageId,
            body: payload.body,
            replyToId: payload.replyToId,
            mentions: payload.mentions,
            attachmentIds: payload.attachmentIds,
          }),
      }
      try {
        const ready = draft.attachments.length > 0 && draft.attachments.every((item) => item.state === 'ready')
        const result = ready
          ? await sendPreparedChatOutboxDraft(draft, deps)
          : await dispatchChatOutboxDraft(
              draft,
              deps,
              {
                onAttachmentState: (localAttachmentId, state, extras) => {
                  patchLocalMessage(draft.clientMessageId, (message) => ({
                    ...message,
                    attachments: message.attachments.map((attachment) =>
                      attachment.localAttachmentId === localAttachmentId
                        ? {
                            ...attachment,
                            state,
                            uploadId: extras?.uploadId ?? attachment.uploadId,
                            progress: extras?.progress ?? attachment.progress,
                          }
                        : attachment,
                    ),
                  }))
                },
              },
              abortController.signal,
            )
        const sent = result as ChatSendMessageResponse | undefined
        try {
          if (sent?.message && establishmentId) {
            appendMessageToCache(establishmentId, draft.conversationId, sent.message, {
              viewerMembershipId,
              activeConversationId,
            })
          }
          await clearChatOutbox({ clientMessageId: draft.clientMessageId })
        } catch {
          console.info('[houston:chat] post-send cleanup failed', {
            clientMessageId: draft.clientMessageId,
            conversationId: draft.conversationId,
          })
        }
        patchLocalMessage(draft.clientMessageId, (message) => ({ ...message, status: 'sent' }))
        setLocalMessages((current) =>
          current.filter((message) => message.clientMessageId !== draft.clientMessageId),
        )
      } catch (error) {
        const rejectCode = error instanceof ChatApiError ? error.code ?? undefined : undefined
        await failMessage(draft, rejectCode)
      } finally {
        abortControllersRef.current.delete(draft.clientMessageId)
        inflightRef.current.delete(draft.clientMessageId)
      }
    },
    [activeConversationId, appendMessageToCache, establishmentId, failMessage, patchLocalMessage, pipelineDeps, viewerMembershipId],
  )

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

      void clearChatOutbox({ clientMessageId: event.message.client_message_id })
      setLocalMessages((current) =>
        current.filter((message) => message.clientMessageId !== event.message.client_message_id),
      )
    },
    [activeConversationId, appendMessageToCache, establishmentId, viewerMembershipId],
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
      void resyncBootstrapAfterLegalError({ code: event.code })
    }
  }, [])

  const clearLocalMessagesForConversation = useCallback((conversationId: string) => {
    void clearChatOutbox({ conversationId })
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
    [clearLocalMessagesForConversation, establishmentId, onConversationAccessRevoked, queryClient],
  )

  const handleGlobalAccessRevoked = useCallback(
    (event: ChatWsGlobalAccessRevokedEvent) => {
      if (establishmentId) {
        void clearChatOutbox({ establishmentId })
      } else {
        void clearChatOutbox()
      }
      onGlobalAccessRevoked?.(event)
    },
    [establishmentId, onGlobalAccessRevoked],
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

    for (const message of localMessagesRef.current) {
      if (message.status !== 'failed') {
        continue
      }
      void loadChatOutboxDrafts({ clientMessageId: message.clientMessageId }).then((drafts) => {
        const draft = drafts[0]
        if (draft) {
          void dispatchDraft({ ...draft, status: 'pending' })
        }
      })
    }
  }, [activeConversationId, dispatchDraft, establishmentId, queryClient])

  const { connectionStatus, reconnect } = useChatWebSocket({
    establishmentId,
    enabled: chatEnabled,
    onMessageCreated: handleMessageCreated,
    onMessageRejected: handleMessageRejected,
    onGlobalAccessRevoked: handleGlobalAccessRevoked,
    onConversationAccessRevoked: handleConversationAccessRevoked,
    onConversationUpdated: handleConversationUpdated,
    onReconnect: handleReconnect,
  })

  useEffect(() => {
    if (!userId || !establishmentId) {
      return
    }
    void clearExpiredChatOutboxAttachments()
    void loadChatOutboxDrafts({ userId, establishmentId }).then((drafts) => {
      setLocalMessages((current) => {
        const existing = new Set(current.map((message) => message.clientMessageId))
        const restored = drafts
          .filter((draft) => !existing.has(draft.clientMessageId))
          .map(draftToLocalMessage)
        return [...current, ...restored]
      })
      for (const draft of drafts) {
        if (draft.status === 'pending') {
          void dispatchDraft(draft)
        }
      }
    })
  }, [dispatchDraft, establishmentId, userId])

  const sendChatMessage = useCallback(
    (payload: SendChatMessagePayload) => {
      const clientMessageId = createClientMessageId()
      const createdAt = new Date().toISOString()
      const files = payload.files ?? []
      if (!establishmentId || !userId) {
        return { clientMessageId, queued: false }
      }

      const attachments: LocalChatAttachment[] = files.map((file) => ({
        localAttachmentId: crypto.randomUUID(),
        uploadId: null,
        filename: file.name,
        contentType: file.type,
        sizeBytes: file.size,
        state: 'reserving',
        previewUrl: file.type.startsWith('image/') ? URL.createObjectURL(file) : undefined,
      }))

      const localMessage: LocalChatMessage = {
        clientMessageId,
        conversationId: payload.conversationId,
        body: payload.body,
        mentions: payload.mentions ?? [],
        replyToId: payload.replyToId ?? null,
        replyPreview: payload.replyPreview ?? null,
        attachments,
        status: 'pending',
        createdAt,
        authorMembershipId: payload.authorMembershipId,
        authorDisplayName: payload.authorDisplayName,
      }

      setLocalMessages((current) => [...current, localMessage])

      void (async () => {
        const persistedAttachments = await Promise.all(
          attachments.map(async (attachment, index) => {
            const file = files[index]
            const relativePath = file
              ? await persistChatOutboxAttachmentBytes({
                  userId,
                  establishmentId,
                  localAttachmentId: attachment.localAttachmentId,
                  blob: file,
                })
              : null
            return {
              localAttachmentId: attachment.localAttachmentId,
              uploadId: attachment.uploadId,
              filename: attachment.filename,
              contentType: attachment.contentType,
              sizeBytes: attachment.sizeBytes,
              state: attachment.state,
              relativePath,
              expiresAt: null,
            }
          }),
        )
        const draft: ChatOutboxDraft = {
          clientMessageId,
          conversationId: payload.conversationId,
          establishmentId,
          userId,
          body: payload.body,
          mentions: payload.mentions ?? [],
          replyToId: payload.replyToId ?? null,
          attachments: persistedAttachments,
          status: 'pending',
          createdAt,
          authorMembershipId: payload.authorMembershipId,
          authorDisplayName: payload.authorDisplayName,
        }
        await saveChatOutboxDraft(draft)
        await dispatchDraft(draft)
      })()

      return { clientMessageId, queued: true }
    },
    [dispatchDraft, establishmentId, userId],
  )

  const retryFailedMessage = useCallback(
    (clientMessageId: string) => {
      const message = localMessagesRef.current.find((item) => item.clientMessageId === clientMessageId)
      if (!message || message.status !== 'failed') {
        return false
      }

      setLocalMessages((current) =>
        current.map((item) =>
          item.clientMessageId === clientMessageId ? asPendingLocalChatMessage(item) : item,
        ),
      )

      void loadChatOutboxDrafts({ clientMessageId }).then((drafts) => {
        const draft = drafts[0]
        if (!draft) {
          return
        }
        void dispatchDraft({ ...draft, status: 'pending' })
      })

      if (connectionStatus === 'disconnected' || connectionStatus === 'reconnecting') {
        void reconnect()
      }

      return true
    },
    [connectionStatus, dispatchDraft, reconnect],
  )

  const cancelSendingMessage = useCallback(
    (clientMessageId: string) => {
      const controller = abortControllersRef.current.get(clientMessageId)
      if (!controller) {
        return false
      }
      controller.abort()
      return true
    },
    [],
  )

  const value = useMemo(
    () => ({
      connectionStatus,
      localMessages,
      sendChatMessage,
      retryFailedMessage,
      cancelSendingMessage,
      clearLocalMessagesForConversation,
      showChatNav: chatEnabled,
      hasUnread,
    }),
    [
      cancelSendingMessage,
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
