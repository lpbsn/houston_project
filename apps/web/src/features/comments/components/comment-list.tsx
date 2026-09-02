import { useEffect } from 'react'

import { MessageCircle } from 'lucide-react'

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
      establishmentId?: string
      onReportComment?: (contentId: string, membershipId: string) => void
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
      Observation
    </HoustonBadge>
  )
}

function SignalCommentItem({
  comment,
  highlightCommentId = null,
  onReportComment,
}: {
  comment: CommentItem
  highlightCommentId?: string | null
  onReportComment?: (contentId: string, membershipId: string) => void
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
        {onReportComment ? (
          <button
            type="button"
            className="text-[11px] text-[#7D7B75] underline"
            onClick={() => onReportComment(comment.id, comment.author.membership_id)}
          >
            Signaler
          </button>
        ) : null}
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
  onReportComment,
}: {
  comments: CommentItem[]
  highlightCommentId?: string | null
  onReportComment?: (contentId: string, membershipId: string) => void
}) {
  useScrollToHighlightedComment(highlightCommentId, comments)

  if (comments.length === 0) {
    return (
      <TerrainEmptyState
        className="flex flex-1 flex-col items-center justify-center border-0 bg-transparent p-6"
        icon={<MessageCircle className="h-10 w-10" strokeWidth={1.5} />}
        title="Aucun commentaire pour l'instant."
        description="Soyez le premier à laisser un commentaire sur cette observation."
      />
    )
  }

  return (
    <ul
      className="mt-3 flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto"
      aria-label="Liste des commentaires"
    >
      {comments.map((comment) => (
        <SignalCommentItem
          key={comment.id}
          comment={comment}
          highlightCommentId={highlightCommentId}
          onReportComment={onReportComment}
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
    return (
      <TerrainEmptyState
        className="flex flex-1 flex-col items-center justify-center border-0 bg-transparent p-6"
        icon={<MessageCircle className="h-10 w-10" strokeWidth={1.5} />}
        title="Aucun commentaire pour l'instant."
        description="Soyez le premier à laisser un commentaire sur ce plan d'action."
      />
    )
  }

  return (
    <ul
      className="mt-4 flex min-h-0 flex-1 flex-col gap-5 overflow-y-auto"
      aria-label="Liste des commentaires"
    >
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
        onReportComment={props.onReportComment}
      />
    )
  }

  return <ExecutionCommentList {...props} />
}

export { CommentOriginBadge }
