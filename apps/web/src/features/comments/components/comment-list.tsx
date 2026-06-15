import { HoustonBadge, TerrainEmptyState } from '@/components/ui/terrain'

import { formatCommentRelativeTime } from '../lib/comment-display'
import type { CommentItem } from '../types'

type CommentListProps = {
  comments: CommentItem[]
  showOrigin?: boolean
}

function CommentOriginBadge({ origin }: { origin: CommentItem['origin'] }) {
  if (origin === 'signal') {
    return (
      <HoustonBadge variant="gray" className="text-[9px]">
        Signal
      </HoustonBadge>
    )
  }

  return (
    <HoustonBadge variant="blue" className="text-[9px]">
      Action
    </HoustonBadge>
  )
}

export function CommentList({ comments, showOrigin = false }: CommentListProps) {
  if (comments.length === 0) {
    return <TerrainEmptyState title="Aucun commentaire pour l'instant." />
  }

  return (
    <ul className="mt-3 flex flex-col gap-3" aria-label="Liste des commentaires">
      {comments.map((comment) => (
        <li
          key={comment.id}
          className="rounded-[12px] border border-[#E8E6DF] bg-[#FAFAF8] px-3 py-3"
        >
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-[13px] font-semibold text-[#1a1a1a]">{comment.author.display_name}</p>
            {showOrigin ? <CommentOriginBadge origin={comment.origin} /> : null}
            <span className="text-[11px] text-[#aaa]">{formatCommentRelativeTime(comment.created_at)}</span>
          </div>
          <p className="mt-2 whitespace-pre-wrap break-words text-[13px] leading-relaxed text-[#444]">
            {comment.body}
          </p>
          {comment.mentions.length > 0 ? (
            <p className="mt-2 text-[11px] text-[#7D7B75]">
              Mentionné : {comment.mentions.map((mention) => mention.display_name).join(', ')}
            </p>
          ) : null}
        </li>
      ))}
    </ul>
  )
}
