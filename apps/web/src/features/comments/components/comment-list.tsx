import { HoustonBadge, TerrainEmptyState } from '@/components/ui/terrain'

import { formatCommentRelativeTime } from '../lib/comment-display'
import type { ActionCommentListItem, CommentCreateRequest, CommentItem } from '../types'
import { isActionThreadItem, isInheritedSignalItem } from '../types'
import {
  ActionCommentThreadCard,
  InheritedSignalCommentCard,
} from './comment-thread-item'

type CommentListProps =
  | {
      mode: 'signal'
      comments: CommentItem[]
    }
  | {
      mode: 'action'
      comments: ActionCommentListItem[]
      establishmentId: string
      disabled?: boolean
      replyErrorCommentId?: string | null
      replyErrorMessage?: string | null
      pendingReplyCommentId?: string | null
      isResolvePending?: boolean
      onReply: (
        payload: CommentCreateRequest,
        callbacks?: { onSuccess?: () => void },
      ) => void
      onResolve: (commentId: string) => void
      onUnresolve: (commentId: string) => void
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

function SignalCommentList({ comments }: { comments: CommentItem[] }) {
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

function ActionCommentList({
  comments,
  establishmentId,
  disabled,
  replyErrorCommentId,
  replyErrorMessage,
  pendingReplyCommentId,
  isResolvePending,
  onReply,
  onResolve,
  onUnresolve,
}: Extract<CommentListProps, { mode: 'action' }>) {
  if (comments.length === 0) {
    return <TerrainEmptyState title="Aucun commentaire pour l'instant." />
  }

  return (
    <ul className="mt-3 flex flex-col gap-3" aria-label="Liste des commentaires">
      {comments.map((item) => {
        if (isInheritedSignalItem(item)) {
          return <InheritedSignalCommentCard key={item.id} item={item} />
        }
        if (isActionThreadItem(item)) {
          return (
            <ActionCommentThreadCard
              key={item.id}
              item={item}
              establishmentId={establishmentId}
              disabled={disabled}
              replyErrorMessage={
                replyErrorCommentId === item.id ? replyErrorMessage : null
              }
              isReplyPending={pendingReplyCommentId === item.id}
              isResolvePending={isResolvePending}
              onReply={onReply}
              onResolve={onResolve}
              onUnresolve={onUnresolve}
            />
          )
        }
        return null
      })}
    </ul>
  )
}

export function CommentList(props: CommentListProps) {
  if (props.mode === 'signal') {
    return <SignalCommentList comments={props.comments} />
  }

  return <ActionCommentList {...props} />
}

// Keep origin badge export for tests that may reference comment list internals.
export { CommentOriginBadge }
