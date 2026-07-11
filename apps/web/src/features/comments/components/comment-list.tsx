import { useEffect } from 'react'

import { HoustonBadge, TerrainEmptyState } from '@/components/ui/terrain'
import { cn } from '@/lib/utils'

import { formatCommentRelativeTime } from '../lib/comment-display'
import {
  COMMENT_SCROLL_ANCHOR_CLASS,
  commentDomId,
  scrollToHighlightedComment,
} from '../lib/comment-highlight'
import type {
  CommentCreateRequest,
  CommentItem,
  ExecutionCommentListItem,
} from '../types'
import { isExecutionInheritedSignalItem, isExecutionThreadItem } from '../types'
import {
  MentionDeepLinkBadge,
  useMentionDeepLinkBadge,
} from './mention-deep-link-badge'
import {
  ActionCommentThreadCard,
  InheritedSignalCommentCard,
} from './comment-thread-item'

type HighlightableListProps = {
  highlightCommentId?: string | null
}

type ThreadedCommentListProps = {
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
} & HighlightableListProps

type CommentListProps =
  | ({
      mode: 'signal'
      comments: CommentItem[]
    } & HighlightableListProps)
  | ({
      mode: 'execution'
      comments: ExecutionCommentListItem[]
    } & ThreadedCommentListProps)

function useScrollToHighlightedComment(
  highlightCommentId: string | null | undefined,
  comments: CommentItem[] | ExecutionCommentListItem[],
) {
  useEffect(() => {
    if (!highlightCommentId) {
      return
    }

    return scrollToHighlightedComment(highlightCommentId)
  }, [comments, highlightCommentId])
}

function CommentOriginBadge({ origin }: { origin: CommentItem['origin'] }) {
  if (origin !== 'signal') {
    return null
  }

  return (
    <HoustonBadge variant="gray" className="text-[9px]">
      Signal
    </HoustonBadge>
  )
}

function SignalCommentItem({
  comment,
  highlightCommentId = null,
}: {
  comment: CommentItem
  highlightCommentId?: string | null
}) {
  const showBadge = useMentionDeepLinkBadge(comment.id, highlightCommentId)

  return (
    <li
      id={commentDomId(comment.id)}
      className={cn(
        'relative rounded-[12px] border border-[#E8E6DF] bg-[#FAFAF8] px-3 py-3',
        COMMENT_SCROLL_ANCHOR_CLASS,
      )}
    >
      {showBadge ? <MentionDeepLinkBadge /> : null}
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
  )
}

function SignalCommentList({
  comments,
  highlightCommentId = null,
}: {
  comments: CommentItem[]
  highlightCommentId?: string | null
}) {
  useScrollToHighlightedComment(highlightCommentId, comments)

  if (comments.length === 0) {
    return <TerrainEmptyState title="Aucun commentaire pour l'instant." />
  }

  return (
    <ul className="mt-3 flex flex-col gap-3" aria-label="Liste des commentaires">
      {comments.map((comment) => (
        <SignalCommentItem
          key={comment.id}
          comment={comment}
          highlightCommentId={highlightCommentId}
        />
      ))}
    </ul>
  )
}

function ExecutionCommentList({
  comments,
  establishmentId,
  disabled,
  replyErrorCommentId,
  replyErrorMessage,
  pendingReplyCommentId,
  isResolvePending,
  highlightCommentId = null,
  onReply,
  onResolve,
  onUnresolve,
}: Extract<CommentListProps, { mode: 'execution' }>) {
  useScrollToHighlightedComment(highlightCommentId, comments)

  if (comments.length === 0) {
    return <TerrainEmptyState title="Aucun commentaire pour l'instant." />
  }

  return (
    <ul className="mt-4 flex flex-col gap-5" aria-label="Liste des commentaires">
      {comments.map((item) => {
        if (isExecutionInheritedSignalItem(item)) {
          return (
            <InheritedSignalCommentCard
              key={item.id}
              item={item}
              highlightCommentId={highlightCommentId}
            />
          )
        }
        if (isExecutionThreadItem(item)) {
          const threadItem = item
          return (
            <ActionCommentThreadCard
              key={item.id}
              item={threadItem}
              establishmentId={establishmentId}
              disabled={disabled}
              highlightCommentId={highlightCommentId}
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
    return (
      <SignalCommentList
        comments={props.comments}
        highlightCommentId={props.highlightCommentId}
      />
    )
  }

  return <ExecutionCommentList {...props} />
}

export { CommentOriginBadge }
