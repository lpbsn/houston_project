import { useEffect, useMemo, useRef } from 'react'
import { LoaderCircle } from 'lucide-react'

import { useAuth } from '@/app/auth-provider'
import { TerrainEmptyState, TerrainErrorState } from '@/components/ui/terrain'
import { resolveApiErrorMessage } from '@/lib/error-message'

import { ChatApiError } from '../api'
import { ChatComposer } from '../components/chat-composer'
import { ChatReconnectBanner } from '../components/chat-reconnect-banner'
import { MessageBubble } from '../components/message-bubble'
import { useOptionalChatRealtime } from '../components/chat-realtime-provider'
import {
  formatChatMessageDayLabel,
  getConversationTitle,
  isSameChatDay,
} from '../lib/chat-display'
import { mergeServerAndLocalMessages } from '../lib/chat-messages'
import {
  useChatConversationDetailQuery,
  useChatMessagesInfiniteQuery,
  useMarkConversationSeenMutation,
} from '../hooks'

type ChatConversationPageProps = {
  conversationId: string
}

export function ChatConversationPage({ conversationId }: ChatConversationPageProps) {
  const auth = useAuth()
  const establishmentId = auth.bootstrap?.active_membership?.establishment_id ?? null
  const viewerMembershipId = auth.bootstrap?.active_membership?.id ?? null
  const viewerDisplayName = auth.bootstrap?.user.username ?? 'Vous'

  const messagesEndRef = useRef<HTMLDivElement | null>(null)
  const detailQuery = useChatConversationDetailQuery(establishmentId, conversationId)
  const messagesQuery = useChatMessagesInfiniteQuery(establishmentId, conversationId)
  const { mutate: markConversationSeen } = useMarkConversationSeenMutation(
    establishmentId,
    conversationId,
  )
  const realtime = useOptionalChatRealtime()
  const connectionStatus = realtime?.connectionStatus ?? 'idle'
  const localMessages = useMemo(
    () => realtime?.localMessages ?? [],
    [realtime?.localMessages],
  )
  const sendChatMessage =
    realtime?.sendChatMessage ??
    (() => ({
      clientMessageId: '',
      queued: false,
    }))
  const retryFailedMessage = realtime?.retryFailedMessage ?? (() => false)

  const serverMessages = useMemo(
    () => messagesQuery.data?.pages.flatMap((page) => page.items) ?? [],
    [messagesQuery.data?.pages],
  )

  const mergedMessages = useMemo(
    () => mergeServerAndLocalMessages(serverMessages, localMessages, conversationId),
    [conversationId, localMessages, serverMessages],
  )

  useEffect(() => {
    if (!establishmentId || !conversationId || !detailQuery.isSuccess) {
      return
    }

    markConversationSeen()
  }, [conversationId, detailQuery.isSuccess, establishmentId, markConversationSeen])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [mergedMessages.length, conversationId])

  if (!establishmentId || !viewerMembershipId) {
    return <p className="px-3 py-4 text-sm text-[#6b5f52]">Établissement non sélectionné.</p>
  }

  if (detailQuery.isLoading || messagesQuery.isLoading) {
    return (
      <div className="flex items-center justify-center py-16 text-[#7D7B75]">
        <LoaderCircle className="h-6 w-6 animate-spin" />
      </div>
    )
  }

  if (detailQuery.isError) {
    return (
      <TerrainErrorState
        className="mx-3 mt-3"
        message={resolveApiErrorMessage(detailQuery.error, ChatApiError, 'Une erreur est survenue.')}
        onRetry={() => void detailQuery.refetch()}
      />
    )
  }

  if (messagesQuery.isError) {
    return (
      <TerrainErrorState
        className="mx-3 mt-3"
        message={resolveApiErrorMessage(messagesQuery.error, ChatApiError, 'Une erreur est survenue.')}
        onRetry={() => void messagesQuery.refetch()}
      />
    )
  }

  const conversationTitle = getConversationTitle(detailQuery.data, viewerMembershipId)

  return (
    <div className="flex h-full min-h-0 flex-col">
      <ChatReconnectBanner status={connectionStatus} />

      <div className="border-b border-[#E8E6DF] bg-white px-3 py-2">
        <p className="text-sm font-semibold text-[#1a1a1a]">{conversationTitle}</p>
        <p className="text-[11px] text-[#7D7B75]">
          Les messages de plus de 7 jours sont automatiquement supprimés.
        </p>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto overscroll-y-contain px-3 py-3">
        {messagesQuery.hasNextPage ? (
          <div className="mb-3 flex justify-center">
            <button
              type="button"
              className="text-xs font-semibold text-[#1B4FD8]"
              onClick={() => void messagesQuery.fetchNextPage()}
              disabled={messagesQuery.isFetchingNextPage}
            >
              {messagesQuery.isFetchingNextPage ? 'Chargement…' : 'Messages plus anciens'}
            </button>
          </div>
        ) : null}

        {mergedMessages.length === 0 ? (
          <TerrainEmptyState
            className="mt-8"
            title="Aucun message"
            description="Envoyez le premier message de cette conversation."
          />
        ) : (
          <div className="flex flex-col gap-3">
            {mergedMessages.map((entry, index) => {
              const createdAt =
                entry.kind === 'server' ? entry.message.created_at : entry.message.createdAt
              const previous = mergedMessages[index - 1]
              const previousCreatedAt = previous
                ? previous.kind === 'server'
                  ? previous.message.created_at
                  : previous.message.createdAt
                : null
              const showDaySeparator =
                !previousCreatedAt || !isSameChatDay(previousCreatedAt, createdAt)

              const message = entry.kind === 'server' ? entry.message : entry.message
              const isOwn =
                entry.kind === 'server'
                  ? entry.message.author_membership_id === viewerMembershipId
                  : entry.message.authorMembershipId === viewerMembershipId

              const key =
                entry.kind === 'server' ? entry.message.id : entry.message.clientMessageId

              return (
                <div key={key} className="flex flex-col gap-3">
                  {showDaySeparator ? (
                    <div className="flex justify-center">
                      <span className="rounded-full bg-white px-3 py-1 text-[11px] font-medium text-[#7D7B75]">
                        {formatChatMessageDayLabel(createdAt)}
                      </span>
                    </div>
                  ) : null}
                  <MessageBubble
                    message={message}
                    isOwn={isOwn}
                    onRetry={
                      entry.kind === 'local' && entry.message.status === 'failed'
                        ? () => {
                            retryFailedMessage(entry.message.clientMessageId)
                          }
                        : undefined
                    }
                  />
                </div>
              )
            })}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      <ChatComposer
        disabled={connectionStatus !== 'connected'}
        onSend={(body) => {
          sendChatMessage({
            conversationId,
            body,
            authorMembershipId: viewerMembershipId,
            authorDisplayName: viewerDisplayName,
          })
        }}
      />
    </div>
  )
}
