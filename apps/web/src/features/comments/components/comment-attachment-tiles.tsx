import { FileText } from 'lucide-react'

import { cn } from '@/lib/utils'

import { CommentAttachmentImage } from './comment-attachment-image'
import {
  isCommentImageAttachment,
  isCommentPdfAttachment,
} from '../lib/comment-media'
import type { CommentAttachment } from '../types'

export function CommentAttachmentTiles({
  attachments,
  onOpen,
}: {
  attachments: CommentAttachment[]
  onOpen: (attachment: CommentAttachment) => void
}) {
  if (attachments.length === 0) {
    return null
  }
  return (
    <ul className="mt-2 flex flex-wrap gap-2">
      {attachments.map((attachment) => (
        <li key={attachment.id}>
          <CommentAttachmentTile attachment={attachment} onOpen={() => onOpen(attachment)} />
        </li>
      ))}
    </ul>
  )
}

function CommentAttachmentTile({
  attachment,
  onOpen,
}: {
  attachment: CommentAttachment
  onOpen: () => void
}) {
  const isImage = isCommentImageAttachment({
    kind: attachment.kind,
    contentType: attachment.content_type,
  })
  const isPdf = isCommentPdfAttachment({
    kind: attachment.kind,
    contentType: attachment.content_type,
  })
  const previewUrl = attachment.preview_url
  const thumbnailUrl = attachment.thumbnail_url ?? previewUrl

  return (
    <button
      type="button"
      onClick={onOpen}
      className={cn(
        'flex max-w-48 items-center gap-2 rounded-xl border border-[#E8E6DF] bg-white px-2 py-1.5 text-left',
      )}
      aria-label={
        isPdf ? `Ouvrir ${attachment.original_filename}` : `Aperçu ${attachment.original_filename}`
      }
    >
      {isImage ? (
        <span className="flex h-10 w-10 shrink-0 items-center justify-center overflow-hidden rounded-lg bg-[#F4F3EF]">
          <CommentAttachmentImage
            src={thumbnailUrl}
            fallbackSrc={previewUrl}
            alt=""
            className="h-full w-full object-cover"
            errorFallback={<span className="text-[10px] text-[#7D7B75]">IMG</span>}
          />
        </span>
      ) : (
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-[#F4F3EF] text-[#1B4FD8]">
          <FileText className="h-5 w-5" />
        </span>
      )}
      <span className="min-w-0 truncate text-[12px] font-medium text-[#1a1a1a]">
        {attachment.original_filename}
      </span>
    </button>
  )
}
