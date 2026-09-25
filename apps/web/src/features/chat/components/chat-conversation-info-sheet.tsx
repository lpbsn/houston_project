import { useEffect, useState, type ReactNode } from 'react'
import { useInfiniteQuery } from '@tanstack/react-query'
import { X } from 'lucide-react'

import { TerrainBottomSheet } from '@/components/ui/terrain'

import { chatQueryKeys, fetchChatSharedMedia } from '../api'
import { formatChatAttachmentSize, formatChatRelativeTime } from '../lib/chat-display'
import { toChatAttachmentPreviewItem, type ChatAttachmentPreviewItem } from '../lib/chat-media'
import { ChatMediaImage } from './message-bubble'
import type { ChatConversationDetail } from '../types'

type ChatConversationInfoSheetProps = {
  establishmentId: string
  conversation: ChatConversationDetail
  open: boolean
  onClose: () => void
  knownMessageIds?: Set<string>
  onSelectAttachment?: (item: ChatAttachmentPreviewItem) => void
  pdfAlert?: string | null
  presentation?: 'sheet' | 'panel'
}

export function ChatConversationInfoSheet({
  establishmentId,
  conversation,
  open,
  onClose,
  knownMessageIds,
  onSelectAttachment,
  pdfAlert,
  presentation = 'sheet',
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

  useEffect(() => {
    if (!open || presentation !== 'panel') {
      return
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        onClose()
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [onClose, open, presentation])

  function selectSharedItem(item: {
    id: string
    original_filename: string
    content_type: string
    kind: string
    preview_url: string
  }) {
    const previewItem = toChatAttachmentPreviewItem({
      id: item.id,
      filename: item.original_filename,
      contentType: item.content_type,
      kind: item.kind,
      src: item.preview_url,
    })
    if (!previewItem) {
      return
    }
    onSelectAttachment?.(previewItem)
  }

  const body: ReactNode = (
    <>
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

      {pdfAlert ? (
        <p className="mb-3 text-sm text-[#E24B4A]" role="alert">
          {pdfAlert}
        </p>
      ) : null}

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
                  onClick={() => selectSharedItem(item)}
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
                <button type="button" className="w-full text-left" onClick={() => selectSharedItem(item)}>
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
    </>
  )

  if (!open) {
    return null
  }

  if (presentation === 'panel') {
    return (
      <aside
        data-testid="chat-conversation-info-panel"
        className="absolute inset-y-0 right-0 z-20 flex w-full max-w-sm flex-col border-l border-[#E8E6DF] bg-white shadow-lg"
        aria-label="Infos conversation"
      >
        <div className="flex items-center justify-between border-b border-[#E8E6DF] px-3 py-2">
          <h2 className="text-sm font-semibold text-[#1a1a1a]">Conversation</h2>
          <button
            type="button"
            className="rounded-md p-1.5 text-[#5c564e] hover:bg-[#F5F4F0]"
            aria-label="Fermer les infos"
            onClick={onClose}
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto px-3 py-3">{body}</div>
      </aside>
    )
  }

  return (
    <TerrainBottomSheet open={open} onClose={onClose} title="Conversation">
      {body}
    </TerrainBottomSheet>
  )
}
