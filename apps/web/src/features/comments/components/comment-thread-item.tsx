import { useState } from 'react'
import { Check, ChevronDown, ChevronUp } from 'lucide-react'

import { HoustonBadge } from '@/components/ui/terrain'
import { getDisplayNameInitials } from '@/lib/display-names'
import { cn } from '@/lib/utils'

import { formatCommentRelativeTime } from '../lib/comment-display'
import type { CommentCreateRequest, ExecutionCommentListItem } from '../types'
import { isExecutionThreadItem } from '../types'
import { CommentComposer } from './comment-composer'

const AVATAR_BG_CLASSES = [
  'bg-[#EEF2FF] text-[#1B4FD8]',
  'bg-[#FFF4E6] text-[#C76B00]',
  'bg-[#E8F5E9] text-[#2E7D32]',
  'bg-[#FCE4EC] text-[#C2185B]',
  'bg-[#F3E5F5] text-[#7B1FA2]',
]

type ReplySubmitCallbacks = {
  onSuccess?: () => void
}

type CommentThreadItemProps = {
  item: ExecutionCommentListItem
  establishmentId: string
  disabled?: boolean
  replyErrorMessage?: string | null
  isReplyPending?: boolean
  isResolvePending?: boolean
  onReply: (payload: CommentCreateRequest, callbacks?: ReplySubmitCallbacks) => void
  onResolve: (commentId: string) => void
  onUnresolve: (commentId: string) => void
}

type CommentContent = Pick<
  ExecutionCommentListItem,
  'author' | 'origin' | 'body' | 'mentions'
>

function getAvatarColorClass(seed: string): string {
  let hash = 0
  for (let index = 0; index < seed.length; index += 1) {
    hash = (hash + seed.charCodeAt(index)) % AVATAR_BG_CLASSES.length
  }
  return AVATAR_BG_CLASSES[hash] ?? AVATAR_BG_CLASSES[0]!
}

function CommentOriginBadge({ origin }: { origin: ExecutionCommentListItem['origin'] }) {
  if (origin !== 'signal') {
    return null
  }

  return (
    <HoustonBadge variant="gray" className="text-[9px]">
      Signal
    </HoustonBadge>
  )
}

function CommentAvatar({
  displayName,
  membershipId,
  size = 'md',
}: {
  displayName: string
  membershipId: string
  size?: 'md' | 'sm'
}) {
  const sizeClass = size === 'sm' ? 'h-6 w-6 text-[10px]' : 'h-8 w-8 text-xs'

  return (
    <span
      className={cn(
        'flex shrink-0 items-center justify-center rounded-full font-semibold',
        sizeClass,
        getAvatarColorClass(membershipId),
      )}
      aria-hidden
    >
      {getDisplayNameInitials(displayName)}
    </span>
  )
}

function CommentBubble({
  comment,
  showOrigin = false,
  isResolved = false,
}: {
  comment: CommentContent
  showOrigin?: boolean
  isResolved?: boolean
}) {
  return (
    <div className="relative min-w-0 flex-1">
      <div className="rounded-2xl bg-[#F0F2F5] px-3 py-2">
        <div className="flex flex-wrap items-center gap-1.5">
          <p className="text-[13px] font-semibold text-[#1a1a1a]">{comment.author.display_name}</p>
          {showOrigin ? <CommentOriginBadge origin={comment.origin} /> : null}
        </div>
        <p className="mt-0.5 whitespace-pre-wrap break-words text-[13px] leading-relaxed text-[#1a1a1a]">
          {comment.body}
        </p>
      </div>
      {isResolved ? <ResolvedTickBadge /> : null}
    </div>
  )
}

function ResolvedTickBadge() {
  return (
    <span
      className="absolute -bottom-1 right-0 flex h-5 w-5 items-center justify-center rounded-full border-2 border-white bg-[#1B4FD8] text-white"
      aria-hidden
    >
      <Check className="h-3 w-3" strokeWidth={3} />
    </span>
  )
}

function CommentMetaRow({
  createdAt,
  canReply,
  canResolve,
  isResolved,
  disabled,
  onReply,
  onToggleResolve,
}: {
  createdAt: string
  canReply: boolean
  canResolve: boolean
  isResolved: boolean
  disabled: boolean
  onReply: () => void
  onToggleResolve: () => void
}) {
  const actions: Array<{
    key: string
    label: string
    ariaLabel: string
    onClick: () => void
    active?: boolean
  }> = []

  if (canResolve) {
    actions.push({
      key: 'resolve',
      label: 'Résolu',
      ariaLabel: isResolved
        ? 'Marquer le commentaire comme non résolu'
        : 'Marquer le commentaire comme résolu',
      onClick: onToggleResolve,
      active: isResolved,
    })
  }

  if (canReply) {
    actions.push({
      key: 'reply',
      label: 'Répondre',
      ariaLabel: 'Répondre au commentaire',
      onClick: onReply,
    })
  }

  return (
    <div className="mt-1 flex flex-wrap items-center gap-1 pl-1">
      <span className="inline-flex min-h-11 items-center px-1 text-[12px] font-semibold text-[#65676B]">
        {formatCommentRelativeTime(createdAt)}
      </span>
      {actions.map((action) => (
        <button
          key={action.key}
          type="button"
          className={cn(
            'inline-flex min-h-11 items-center px-2 text-[12px] font-semibold',
            action.active ? 'text-[#137333]' : 'text-[#65676B]',
          )}
          disabled={disabled}
          onClick={action.onClick}
          aria-label={action.ariaLabel}
        >
          {action.label}
        </button>
      ))}
    </div>
  )
}

function CommentRow({
  comment,
  showOrigin = false,
  isResolved = false,
  avatarSize = 'md',
}: {
  comment: CommentContent & { author: { membership_id: string; display_name: string } }
  showOrigin?: boolean
  isResolved?: boolean
  avatarSize?: 'md' | 'sm'
}) {
  return (
    <div className="flex gap-2">
      <CommentAvatar
        displayName={comment.author.display_name}
        membershipId={comment.author.membership_id}
        size={avatarSize}
      />
      <CommentBubble comment={comment} showOrigin={showOrigin} isResolved={isResolved} />
    </div>
  )
}

export function InheritedSignalCommentCard({ item }: { item: ExecutionCommentListItem }) {
  return (
    <li>
      <CommentRow comment={item} showOrigin />
    </li>
  )
}

export function ActionCommentThreadCard({
  item,
  establishmentId,
  disabled = false,
  replyErrorMessage = null,
  isReplyPending = false,
  isResolvePending = false,
  onReply,
  onResolve,
  onUnresolve,
}: CommentThreadItemProps) {
  const isThread = isExecutionThreadItem(item)
  const [expanded, setExpanded] = useState(!(item.is_resolved ?? false))
  const [isReplying, setIsReplying] = useState(false)

  if (!isThread) {
    return null
  }

  const replyCount = item.replies?.length ?? 0
  const hints = item.permission_hints
  const isResolved = item.is_resolved ?? false
  const isActionDisabled = disabled || isReplyPending || isResolvePending

  return (
    <li>
      <CommentRow comment={item} showOrigin isResolved={isResolved} />

      <div className="ml-10">
        <CommentMetaRow
          createdAt={item.created_at}
          canReply={hints?.can_reply ?? false}
          canResolve={hints?.can_resolve ?? false}
          isResolved={isResolved}
          disabled={isActionDisabled}
          onReply={() => setIsReplying((current) => !current)}
          onToggleResolve={() => {
            if (isResolved) {
              onUnresolve(item.id)
              return
            }
            onResolve(item.id)
          }}
        />

        {isReplying ? (
          <div className="mt-1">
            <CommentComposer
              variant="reply"
              establishmentId={establishmentId}
              disabled={disabled || isReplyPending}
              errorMessage={replyErrorMessage}
              placeholder={`Répondre à ${item.author.display_name}…`}
              showCancel
              onCancel={() => setIsReplying(false)}
              onSubmit={({ body, mentionedMembershipIds }) => {
                onReply(
                  {
                    body,
                    mentioned_membership_ids: mentionedMembershipIds,
                    parent_comment_id: item.id,
                  },
                  {
                    onSuccess: () => {
                      setIsReplying(false)
                    },
                  },
                )
              }}
            />
          </div>
        ) : null}

        {replyCount > 0 ? (
          <div className="mt-1">
            <button
              type="button"
              className="flex min-h-11 items-center gap-1 px-1 text-[12px] font-semibold text-[#65676B]"
              onClick={() => setExpanded((current) => !current)}
              aria-expanded={expanded}
              aria-label={
                expanded
                  ? 'Masquer les réponses'
                  : `Voir ${replyCount} réponse${replyCount > 1 ? 's' : ''}`
              }
            >
              {expanded ? (
                <>
                  <ChevronUp className="h-4 w-4" />
                  Masquer
                </>
              ) : (
                <>
                  <ChevronDown className="h-4 w-4" />
                  Voir {replyCount} réponse{replyCount > 1 ? 's' : ''}
                </>
              )}
            </button>

            {expanded ? (
              <ul className={cn('mt-1 flex flex-col gap-3 border-l-2 border-[#E4E6EB] pl-3')}>
                {(item.replies ?? []).map((reply) => (
                  <li key={reply.id}>
                    <CommentRow comment={reply} avatarSize="sm" />
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
        ) : null}
      </div>
    </li>
  )
}
