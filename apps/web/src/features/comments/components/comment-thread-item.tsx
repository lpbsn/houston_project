import { useState } from 'react'
import { ChevronDown, ChevronUp } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { HoustonBadge } from '@/components/ui/terrain'
import { cn } from '@/lib/utils'

import { formatCommentRelativeTime } from '../lib/comment-display'
import type { ActionCommentListItem, CommentCreateRequest } from '../types'
import { isActionThreadItem } from '../types'
import { CommentComposer } from './comment-composer'

type ReplySubmitCallbacks = {
  onSuccess?: () => void
}

type CommentThreadItemProps = {
  item: ActionCommentListItem
  establishmentId: string
  disabled?: boolean
  replyErrorMessage?: string | null
  isReplyPending?: boolean
  isResolvePending?: boolean
  onReply: (payload: CommentCreateRequest, callbacks?: ReplySubmitCallbacks) => void
  onResolve: (commentId: string) => void
  onUnresolve: (commentId: string) => void
}

function CommentOriginBadge({ origin }: { origin: ActionCommentListItem['origin'] }) {
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

function ResolvedBadge() {
  return (
    <HoustonBadge variant="gray" className="bg-[#E6F4EA] text-[9px] text-[#137333]">
      Résolu
    </HoustonBadge>
  )
}

function CommentBody({
  comment,
  showOrigin = false,
}: {
  comment: Pick<ActionCommentListItem, 'author' | 'origin' | 'created_at' | 'body' | 'mentions'>
  showOrigin?: boolean
}) {
  return (
    <>
      <div className="flex flex-wrap items-center gap-2">
        <p className="text-[13px] font-semibold text-[#1a1a1a]">{comment.author.display_name}</p>
        {showOrigin ? <CommentOriginBadge origin={comment.origin} /> : null}
        <span className="text-[11px] text-[#aaa]">
          {formatCommentRelativeTime(comment.created_at)}
        </span>
      </div>
      <p className="mt-2 whitespace-pre-wrap break-words text-[13px] leading-relaxed text-[#444]">
        {comment.body}
      </p>
      {comment.mentions.length > 0 ? (
        <p className="mt-2 text-[11px] text-[#7D7B75]">
          Mentionné : {comment.mentions.map((mention) => mention.display_name).join(', ')}
        </p>
      ) : null}
    </>
  )
}

export function InheritedSignalCommentCard({ item }: { item: ActionCommentListItem }) {
  return (
    <li className="rounded-[12px] border border-[#E8E6DF] bg-[#FAFAF8] px-3 py-3">
      <CommentBody comment={item} showOrigin />
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
  const isThread = isActionThreadItem(item)
  const [expanded, setExpanded] = useState(!(item.is_resolved ?? false))
  const [isReplying, setIsReplying] = useState(false)

  if (!isThread) {
    return null
  }

  const replyCount = item.replies?.length ?? 0
  const hints = item.permission_hints

  return (
    <li className="rounded-[12px] border border-[#E8E6DF] bg-[#FAFAF8] px-3 py-3">
      <div className="flex flex-wrap items-center gap-2">
        <p className="text-[13px] font-semibold text-[#1a1a1a]">{item.author.display_name}</p>
        <CommentOriginBadge origin={item.origin} />
        {item.is_resolved ? <ResolvedBadge /> : null}
        <span className="text-[11px] text-[#aaa]">
          {formatCommentRelativeTime(item.created_at)}
        </span>
      </div>

      <p className="mt-2 whitespace-pre-wrap break-words text-[13px] leading-relaxed text-[#444]">
        {item.body}
      </p>

      {item.mentions.length > 0 ? (
        <p className="mt-2 text-[11px] text-[#7D7B75]">
          Mentionné : {item.mentions.map((mention) => mention.display_name).join(', ')}
        </p>
      ) : null}

      <div className="mt-3 flex flex-wrap gap-2">
        {hints?.can_reply ? (
          <Button
            type="button"
            variant="outline"
            className="min-h-11 rounded-full border-[#E8E6DF] px-3 text-[12px]"
            disabled={disabled || isReplyPending || isResolvePending}
            onClick={() => setIsReplying((current) => !current)}
            aria-label="Répondre au commentaire"
          >
            Répondre
          </Button>
        ) : null}
        {hints?.can_resolve && !item.is_resolved ? (
          <Button
            type="button"
            variant="outline"
            className="min-h-11 rounded-full border-[#E8E6DF] px-3 text-[12px]"
            disabled={disabled || isReplyPending || isResolvePending}
            onClick={() => onResolve(item.id)}
            aria-label="Marquer le commentaire comme résolu"
          >
            Marquer résolu
          </Button>
        ) : null}
        {hints?.can_resolve && item.is_resolved ? (
          <Button
            type="button"
            variant="outline"
            className="min-h-11 rounded-full border-[#E8E6DF] px-3 text-[12px]"
            disabled={disabled || isReplyPending || isResolvePending}
            onClick={() => onUnresolve(item.id)}
            aria-label="Marquer le commentaire comme non résolu"
          >
            Marquer non résolu
          </Button>
        ) : null}
      </div>

      {isReplying ? (
        <div className="mt-3 border-t border-[#E8E6DF] pt-3">
          <CommentComposer
            establishmentId={establishmentId}
            disabled={disabled || isReplyPending}
            errorMessage={replyErrorMessage}
            placeholder="Répondre..."
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
        <div className="mt-3">
          <button
            type="button"
            className="flex min-h-11 items-center gap-1 text-[12px] font-medium text-[#1B4FD8]"
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
            <ul className={cn('mt-2 flex flex-col gap-2 border-l border-[#E8E6DF] pl-3')}>
              {(item.replies ?? []).map((reply) => (
                <li key={reply.id} className="rounded-[10px] bg-white px-2 py-2">
                  <CommentBody comment={reply} />
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}
    </li>
  )
}
