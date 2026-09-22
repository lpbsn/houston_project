import { useState } from 'react'

import { TerrainBottomSheet } from '@/components/ui/terrain'

import { useCommentMediaObjectUrl } from '../hooks/use-comment-media-object-url'
import { formatCommentAttachmentSize, formatCommentRelativeTime } from '../lib/comment-display'
import { isCommentImageAttachment, isCommentPdfAttachment } from '../lib/comment-media'
import type { CommentAttachment } from '../types'

type ExecutionPlanInfoSheetProps = {
  attachments: CommentAttachment[]
  open: boolean
  onClose: () => void
  onOpen: (attachment: CommentAttachment) => void
  onJumpToOrigin: (commentId: string) => void
}

export function ExecutionPlanInfoSheet({
  attachments,
  open,
  onClose,
  onOpen,
  onJumpToOrigin,
}: ExecutionPlanInfoSheetProps) {
  const [tab, setTab] = useState<'media' | 'documents'>('media')
  const mediaItems = attachments.filter((attachment) =>
    isCommentImageAttachment({
      kind: attachment.kind,
      contentType: attachment.content_type,
    }),
  )
  const documentItems = attachments.filter((attachment) =>
    isCommentPdfAttachment({
      kind: attachment.kind,
      contentType: attachment.content_type,
    }),
  )
  const items = tab === 'media' ? mediaItems : documentItems

  function jumpToOrigin(commentId: string) {
    onClose()
    onJumpToOrigin(commentId)
  }

  return (
    <TerrainBottomSheet open={open} onClose={onClose} title="Médias">
      <div className="flex flex-wrap gap-2 pb-3">
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

      {items.length === 0 ? (
        <p className="text-sm text-[#7D7B75]">
          {tab === 'media' ? 'Aucun média partagé.' : 'Aucun document partagé.'}
        </p>
      ) : tab === 'media' ? (
        <ul className="grid grid-cols-[repeat(auto-fill,minmax(5.5rem,5.5rem))] justify-start gap-2">
          {mediaItems.map((attachment) => (
            <li key={attachment.id} className="w-[5.5rem]">
              <PlanInfoMediaTile attachment={attachment} onOpen={() => onOpen(attachment)} />
              <button
                type="button"
                className="mt-1 text-[10px] font-medium text-[#1B4FD8]"
                onClick={() => jumpToOrigin(attachment.comment_id)}
              >
                Voir le commentaire d’origine
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <ul className="space-y-2">
          {documentItems.map((attachment) => (
            <li key={attachment.id} className="rounded-xl bg-[#F5F4F0] px-3 py-2">
              <button type="button" className="w-full text-left" onClick={() => onOpen(attachment)}>
                <p className="text-sm font-medium text-[#1a1a1a]">{attachment.original_filename}</p>
                <p className="text-[11px] text-[#7D7B75]">
                  {formatCommentAttachmentSize(attachment.size_bytes)} ·{' '}
                  {attachment.author_display_name} · {formatCommentRelativeTime(attachment.created_at)}
                </p>
              </button>
              <button
                type="button"
                className="mt-1 text-[11px] font-medium text-[#1B4FD8]"
                onClick={() => jumpToOrigin(attachment.comment_id)}
              >
                Voir le commentaire d’origine
              </button>
            </li>
          ))}
        </ul>
      )}
    </TerrainBottomSheet>
  )
}

function PlanInfoMediaTile({
  attachment,
  onOpen,
}: {
  attachment: CommentAttachment
  onOpen: () => void
}) {
  const { objectUrl, loading } = useCommentMediaObjectUrl(
    attachment.thumbnail_url ?? attachment.preview_url,
  )

  return (
    <button
      type="button"
      className="block h-[5.5rem] w-[5.5rem] overflow-hidden rounded-lg"
      aria-label={attachment.original_filename}
      onClick={onOpen}
    >
      {objectUrl ? (
        <img src={objectUrl} alt="" className="h-full w-full object-cover" />
      ) : (
        <span className="flex h-full w-full items-center justify-center bg-[#F4F3EF] text-[10px] text-[#7D7B75]">
          {loading ? '…' : 'IMG'}
        </span>
      )}
    </button>
  )
}
