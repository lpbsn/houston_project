import { useState } from 'react'
import { useInfiniteQuery } from '@tanstack/react-query'

import { TerrainBottomSheet } from '@/components/ui/terrain'

import { chatQueryKeys, fetchChatSharedMedia } from '../api'
import type { ChatConversationDetail } from '../types'

type ChatConversationInfoSheetProps = {
  establishmentId: string
  conversation: ChatConversationDetail
  open: boolean
  onClose: () => void
}

export function ChatConversationInfoSheet({
  establishmentId,
  conversation,
  open,
  onClose,
}: ChatConversationInfoSheetProps) {
  const [tab, setTab] = useState<'participants' | 'media'>('participants')
  const mediaQuery = useInfiniteQuery({
    queryKey: chatQueryKeys.sharedMedia(establishmentId, conversation.id),
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam }) =>
      fetchChatSharedMedia(establishmentId, conversation.id, { cursor: pageParam }),
    getNextPageParam: (lastPage) => (lastPage.has_more ? lastPage.cursor ?? undefined : undefined),
    enabled: open && tab === 'media',
  })
  const mediaItems = mediaQuery.data?.pages.flatMap((page) => page.items) ?? []

  return (
    <TerrainBottomSheet open={open} onClose={onClose} title="Conversation">
      <div className="flex gap-2 pb-3">
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
          Médias et documents
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
      ) : (
        <div className="space-y-2">
          {mediaItems.length === 0 && !mediaQuery.isLoading ? (
            <p className="text-sm text-[#7D7B75]">Aucun média partagé.</p>
          ) : (
            <ul className="space-y-2">
              {mediaItems.map((item) => (
                <li key={item.id}>
                  <a
                    href={item.preview_url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-sm font-medium text-[#1B4FD8] underline"
                  >
                    {item.original_filename}
                  </a>
                </li>
              ))}
            </ul>
          )}
          {mediaQuery.hasNextPage ? (
            <button
              type="button"
              className="text-xs font-semibold text-[#1B4FD8]"
              onClick={() => void mediaQuery.fetchNextPage()}
            >
              Charger plus
            </button>
          ) : null}
        </div>
      )}
    </TerrainBottomSheet>
  )
}
