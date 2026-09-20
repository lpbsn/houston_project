import { useState } from 'react'
import { useInfiniteQuery } from '@tanstack/react-query'

import { TerrainBottomSheet } from '@/components/ui/terrain'

import { chatQueryKeys, fetchChatSharedMedia } from '../api'
import { formatChatAttachmentSize, formatChatRelativeTime } from '../lib/chat-display'
import { ChatMediaImage } from './message-bubble'
import type { ChatAttachment, ChatConversationDetail } from '../types'

type ChatConversationInfoSheetProps = {
  establishmentId: string
  conversation: ChatConversationDetail
  open: boolean
  onClose: () => void
  knownMessageIds?: Set<string>
  onJumpToMessage?: (messageId: string) => void
}

export function ChatConversationInfoSheet({
  establishmentId,
  conversation,
  open,
  onClose,
  knownMessageIds,
  onJumpToMessage,
}: ChatConversationInfoSheetProps) {
  const [tab, setTab] = useState<'participants' | 'media' | 'documents'>('participants')
  const kind = tab === 'media' ? 'image' : tab === 'documents' ? 'document' : null
  const mediaQuery = useInfiniteQuery({
    queryKey: chatQueryKeys.sharedMedia(establishmentId, conversation.id, kind),
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam }) =>
      fetchChatSharedMedia(establishmentId, conversation.id, {
        cursor: pageParam,
        kind: kind ?? undefined,
      }),
    getNextPageParam: (lastPage) => (lastPage.has_more ? lastPage.cursor ?? undefined : undefined),
    enabled: open && kind !== null,
  })
  const mediaItems = mediaQuery.data?.pages.flatMap((page) => page.items) ?? []

  function jump(item: ChatAttachment) {
    const messageId = item.message_id
    if (!messageId) {
      return
    }
    if (knownMessageIds && !knownMessageIds.has(messageId)) {
      return
    }
    onJumpToMessage?.(messageId)
    onClose()
  }

  return (
    <TerrainBottomSheet open={open} onClose={onClose} title="Conversation">
      <div className="flex flex-wrap gap-2 pb-3">
        <button
          type="button"
          className={`rounded-full px-3 py-1.5 text-xs font-semibold ${
            tab === 'participants' ? 'bg-[#1a1a1a] text-white' : 'bg-[#F5F4F0] text-[#1a1a1a]'
          }`}
          onClick={() => setTab('participants')}
        >
          Participants
        </button>
        <button
          type="button"
          className={`rounded-full px-3 py-1.5 text-xs font-semibold ${
            tab === 'media' ? 'bg-[#1a1a1a] text-white' : 'bg-[#F5F4F0] text-[#1a1a1a]'
          }`}
          onClick={() => setTab('media')}
        >
          Médias
        </button>
        <button
          type="button"
          className={`rounded-full px-3 py-1.5 text-xs font-semibold ${
            tab === 'documents' ? 'bg-[#1a1a1a] text-white' : 'bg-[#F5F4F0] text-[#1a1a1a]'
          }`}
          onClick={() => setTab('documents')}
        >
          Documents
        </button>
      </div>

      {tab === 'participants' ? (
        <ul className="space-y-2">
          {conversation.participants.map((participant) => (
            <li key={participant.membership_id} className="rounded-xl bg-[#F5F4F0] px-3 py-2">
              <p className="text-sm font-semibold text-[#1a1a1a]">{participant.display_name}</p>
              <p className="text-[11px] text-[#7D7B75]">{participant.role}</p>
            </li>
          ))}
        </ul>
      ) : mediaItems.length === 0 && !mediaQuery.isLoading ? (
        <p className="text-sm text-[#7D7B75]">
          {tab === 'media' ? 'Aucun média partagé.' : 'Aucun document partagé.'}
        </p>
      ) : tab === 'media' ? (
        <ul className="grid grid-cols-3 gap-2">
          {mediaItems.map((item) => {
            const available = !knownMessageIds || knownMessageIds.has(item.message_id)
            return (
              <li key={item.id}>
                <button
                  type="button"
                  className="block w-full overflow-hidden rounded-lg"
                  onClick={() => jump(item)}
                >
                  <ChatMediaImage
                    src={item.thumbnail_url ?? item.preview_url}
                    alt={item.original_filename}
                  />
                </button>
                {!available ? (
                  <p className="mt-1 text-[10px] text-[#7D7B75]">Message d’origine indisponible</p>
                ) : null}
              </li>
            )
          })}
        </ul>
      ) : (
        <ul className="space-y-2">
          {mediaItems.map((item) => {
            const available = !knownMessageIds || knownMessageIds.has(item.message_id)
            return (
              <li key={item.id} className="rounded-xl bg-[#F5F4F0] px-3 py-2">
                <button type="button" className="w-full text-left" onClick={() => jump(item)}>
                  <p className="text-sm font-medium text-[#1a1a1a]">{item.original_filename}</p>
                  <p className="text-[11px] text-[#7D7B75]">
                    {item.content_type} · {formatChatAttachmentSize(item.size_bytes)} ·{' '}
                    {item.author_display_name} · {formatChatRelativeTime(item.created_at)}
                  </p>
                  {!available ? (
                    <p className="text-[11px] text-[#7D7B75]">Message d’origine indisponible</p>
                  ) : null}
                </button>
              </li>
            )
          })}
        </ul>
      )}
      {kind && mediaQuery.hasNextPage ? (
        <button
          type="button"
          className="mt-3 text-xs font-semibold text-[#1B4FD8]"
          onClick={() => void mediaQuery.fetchNextPage()}
        >
          Charger plus
        </button>
      ) : null}
    </TerrainBottomSheet>
  )
}
