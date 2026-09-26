import { useEffect } from 'react'

import { MessageCircle } from 'lucide-react'

import { TerrainEmptyState } from '@/components/ui/terrain'
import { getDisplayNameInitials } from '@/lib/display-names'
import { commentThread } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

import { formatCommentRelativeTime } from '../lib/comment-display'
import {
  COMMENT_SCROLL_ANCHOR_CLASS,
  commentDomId,
  scrollToHighlightedComment,
} from '../lib/comment-highlight'
import type {
  CommentAttachment,
  CommentItem,
  ExecutionCommentCreateRequest,
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
    payload: ExecutionCommentCreateRequest,
    callbacks?: { onSuccess?: () => void },
  ) => void
  onResolve: (commentId: string) => void
  onUnresolve: (commentId: string) => void
  onOpenAttachment?: (attachment: CommentAttachment) => void
  attachEnabled?: boolean
  attachTrigger?: 'label' | 'icon'
  executionId?: string
  documentFlow?: boolean
} & HighlightableListProps

type CommentListProps =
  | ({
      mode: 'signal'
      comments: CommentItem[]
      establishmentId?: string
      documentFlow?: boolean
      onReportComment?: (contentId: string, membershipId: string) => void
    } & HighlightableListProps)
  | ({
      mode: 'execution'
      comments: ExecutionCommentListItem[]
    } & ThreadedCommentListProps)

const AVATAR_BG_CLASSES = [
  'bg-[#EEF2FF] text-[#1B4FD8]',
  'bg-[#FFF4E6] text-[#C76B00]',
  'bg-[#E8F5E9] text-[#2E7D32]',
  'bg-[#FCE4EC] text-[#C2185B]',
  'bg-[#F3E5F5] text-[#7B1FA2]',
]

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

function getAvatarColorClass(seed: string): string {
  let hash = 0
  for (let index = 0; index < seed.length; index += 1) {
    hash = (hash + seed.charCodeAt(index)) % AVATAR_BG_CLASSES.length
  }
  return AVATAR_BG_CLASSES[hash] ?? AVATAR_BG_CLASSES[0]!
}

function SignalCommentAvatar({
  displayName,
  membershipId,
}: {
  displayName: string
  membershipId: string
}) {
  return (
    <span
      className={cn(
        'flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-semibold',
        getAvatarColorClass(membershipId),
      )}
      aria-hidden
    >
      {getDisplayNameInitials(displayName)}
    </span>
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
    <li id={commentDomId(comment.id)} className={COMMENT_SCROLL_ANCHOR_CLASS}>
      <div className="flex gap-2">
        <SignalCommentAvatar
          displayName={comment.author.display_name}
          membershipId={comment.author.membership_id}
        />
        <div className="relative min-w-0 flex-1">
          <div className={cn('rounded-2xl px-4 py-3', commentThread.bubbleBg)}>
            <p className="text-[13px] font-semibold text-[#1a1a1a]">{comment.author.display_name}</p>
            <p className="mt-0.5 whitespace-pre-wrap break-words text-[13px] leading-relaxed text-[#1a1a1a]">
              {comment.body}
            </p>
            {comment.mentions.length > 0 ? (
              <p className="mt-1.5 text-[11px] text-[#7D7B75]">
                Mentionné : {comment.mentions.map((mention) => mention.display_name).join(', ')}
              </p>
            ) : null}
          </div>
          {showBadge ? <MentionDeepLinkBadge /> : null}
          <div className="mt-1 flex flex-wrap items-center gap-1.5 pl-1">
            <span
              className={cn(
                'inline-flex min-h-8 items-center px-1 text-[12px] font-semibold',
                commentThread.metaMuted,
              )}
            >
              {formatCommentRelativeTime(comment.created_at)}
            </span>
            {onReportComment ? (
              <button
                type="button"
                className={cn(
                  'inline-flex min-h-8 items-center px-1.5 text-[12px] font-semibold',
                  commentThread.metaMuted,
                )}
                onClick={() => onReportComment(comment.id, comment.author.membership_id)}
              >
                Signaler
              </button>
            ) : null}
          </div>
        </div>
      </div>
    </li>
  )
}

function SignalCommentList({
  comments,
  highlightCommentId = null,
  documentFlow = false,
  onReportComment,
}: {
  comments: CommentItem[]
  highlightCommentId?: string | null
  documentFlow?: boolean
  onReportComment?: (contentId: string, membershipId: string) => void
}) {
  useScrollToHighlightedComment(highlightCommentId, comments)

  if (comments.length === 0) {
    return (
      <TerrainEmptyState
        className={cn(
          'flex flex-col items-center justify-center border-0 bg-transparent p-6',
          documentFlow ? 'py-10' : 'flex-1',
        )}
        icon={<MessageCircle className="h-10 w-10" strokeWidth={1.5} />}
        title="Aucun commentaire pour l'instant."
        description="Soyez le premier à laisser un commentaire sur cette observation."
      />
    )
  }

  return (
    <ul
      className={cn(
        'mt-3 flex flex-col gap-4',
        documentFlow ? '' : 'min-h-0 flex-1 gap-3 overflow-y-auto',
      )}
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
  onOpenAttachment,
  attachEnabled,
  attachTrigger,
  executionId,
  documentFlow = false,
}: Extract<CommentListProps, { mode: 'execution' }>) {
  useScrollToHighlightedComment(highlightCommentId, comments)

  if (comments.length === 0) {
    return (
      <TerrainEmptyState
        className={cn(
          'flex flex-col items-center justify-center border-0 bg-transparent p-6',
          documentFlow ? 'py-10' : 'flex-1',
        )}
        icon={<MessageCircle className="h-10 w-10" strokeWidth={1.5} />}
        title="Aucun commentaire pour l'instant."
        description="Soyez le premier à laisser un commentaire sur ce plan d'action."
      />
    )
  }

  return (
    <ul
      className={cn(
        'mt-4 flex flex-col gap-5',
        documentFlow ? '' : 'min-h-0 flex-1 overflow-y-auto',
      )}
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
              onOpenAttachment={onOpenAttachment}
              attachEnabled={attachEnabled}
              attachTrigger={attachTrigger}
              executionId={executionId}
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
        documentFlow={props.documentFlow}
        onReportComment={props.onReportComment}
      />
    )
  }

  return <ExecutionCommentList {...props} />
}
