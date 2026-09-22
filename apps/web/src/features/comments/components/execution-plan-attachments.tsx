import { commentDomId, scrollToHighlightedComment } from '../lib/comment-highlight'
import type { CommentAttachment } from '../types'
import { CommentAttachmentTiles } from './comment-attachment-tiles'

export function ExecutionPlanAttachments({
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
    <section className="mb-3" data-testid="execution-plan-attachments">
      <h3 className="text-[13px] font-semibold text-[#1a1a1a]">Pièces jointes du plan</h3>
      <CommentAttachmentTiles
        attachments={attachments}
        onOpen={(attachment) => {
          onOpen(attachment)
        }}
      />
      <ul className="mt-1 space-y-0.5">
        {attachments.map((attachment) => (
          <li key={`${attachment.id}-origin`}>
            <button
              type="button"
              className="text-[11px] font-medium text-[#1B4FD8]"
              onClick={() => {
                const element = document.getElementById(commentDomId(attachment.comment_id))
                if (element) {
                  scrollToHighlightedComment(attachment.comment_id)
                }
              }}
            >
              Voir le commentaire d’origine · {attachment.original_filename}
            </button>
          </li>
        ))}
      </ul>
    </section>
  )
}
