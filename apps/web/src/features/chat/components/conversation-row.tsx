import type { KeyboardEvent, MouseEvent } from 'react'
import { MoreHorizontal, Pin } from 'lucide-react'

import { terrainBrandAction, terrainFeedAvatar } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

import {
  formatChatRelativeTime,
  formatUnreadBadgeCount,
  getConversationAvatarInitials,
  getConversationTitle,
  getUnreadCountAriaLabel,
} from '../lib/chat-display'
import type { ChatConversationListItem } from '../types'
import {
  ChatConversationActionsPopover,
  type ChatConversationActionsHandlers,
} from './chat-conversation-actions-sheet'

type ConversationRowProps = {
  conversation: ChatConversationListItem
  viewerMembershipId: string | null
  onSelect: (conversationId: string) => void
  /** Required for sheet mode; unused when `actionsMode` is `popover`. */
  onOpenActions?: (conversation: ChatConversationListItem) => void
  selected?: boolean
  actionsMode?: 'sheet' | 'popover'
  actionsOpen?: boolean
  onActionsOpenChange?: (open: boolean) => void
  actionsPending?: boolean
  actionsErrorMessage?: string | null
  actionHandlers?: ChatConversationActionsHandlers
}

type ConversationAvatarButtonProps = {
  conversation: ChatConversationListItem
  viewerMembershipId: string | null
  selected?: boolean
  onSelect: (conversationId: string) => void
}

function handleRowKeyDown(
  event: KeyboardEvent<HTMLElement>,
  onSelect: (conversationId: string) => void,
  conversationId: string,
) {
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault()
    onSelect(conversationId)
  }
}

function ConversationAvatarFace({
  conversation,
  viewerMembershipId,
  className,
}: {
  conversation: ChatConversationListItem
  viewerMembershipId: string | null
  className?: string
}) {
  const isGroup = conversation.type === 'group'
  const initials = getConversationAvatarInitials(conversation, viewerMembershipId)

  return (
    <span
      className={cn(
        'flex shrink-0 items-center justify-center rounded-full text-xs font-semibold',
        isGroup ? cn(terrainBrandAction.bg, 'text-white') : terrainFeedAvatar,
        className,
      )}
      aria-hidden="true"
    >
      {initials}
    </span>
  )
}

export function ConversationAvatarButton({
  conversation,
  viewerMembershipId,
  selected = false,
  onSelect,
}: ConversationAvatarButtonProps) {
  const title = getConversationTitle(conversation, viewerMembershipId)

  return (
    <button
      type="button"
      className={cn(
        'relative flex h-10 w-10 items-center justify-center rounded-full outline-none transition focus-visible:ring-2 focus-visible:ring-[#114660]/30 focus-visible:ring-offset-2',
        selected && 'ring-2 ring-[#114660]/25 ring-offset-2',
      )}
      aria-label={title}
      title={title}
      aria-current={selected ? 'true' : undefined}
      data-testid={`chat-conversation-avatar-${conversation.id}`}
      onClick={() => onSelect(conversation.id)}
    >
      <ConversationAvatarFace
        conversation={conversation}
        viewerMembershipId={viewerMembershipId}
        className="h-9 w-9"
      />
      {conversation.unread_count > 0 ? (
        <span
          className="absolute -right-0.5 -top-0.5 inline-flex min-h-[16px] min-w-[16px] items-center justify-center rounded-full bg-[#4c8543] px-0.5 text-[10px] font-semibold leading-none text-white"
          aria-label={getUnreadCountAriaLabel(conversation.unread_count)}
        >
          {formatUnreadBadgeCount(conversation.unread_count)}
        </span>
      ) : null}
    </button>
  )
}

export function ConversationRow({
  conversation,
  viewerMembershipId,
  onSelect,
  onOpenActions,
  selected = false,
  actionsMode = 'sheet',
  actionsOpen = false,
  onActionsOpenChange,
  actionsPending = false,
  actionsErrorMessage = null,
  actionHandlers,
}: ConversationRowProps) {
  const title = getConversationTitle(conversation, viewerMembershipId)
  const preview = conversation.last_message_preview?.body?.trim() || 'Aucun message'
  const isUnread = conversation.unread
  const unreadCount = conversation.unread_count

  function handleActionsClick(event: MouseEvent<HTMLButtonElement>) {
    event.preventDefault()
    event.stopPropagation()
    onOpenActions?.(conversation)
  }

  return (
    <article
      className={cn(
        'cursor-pointer rounded-[22px] border bg-white py-2 px-3 transition',
        isUnread ? 'border-[#4c8543]/35' : 'border-[#E8E6DF]',
        selected && 'ring-2 ring-[#114660]/25',
      )}
      onClick={() => onSelect(conversation.id)}
      onKeyDown={(event) => handleRowKeyDown(event, onSelect, conversation.id)}
      role="button"
      tabIndex={0}
      aria-current={selected ? 'true' : undefined}
      data-testid={`chat-conversation-row-${conversation.id}`}
    >
      <div className="flex items-center gap-2.5">
        <ConversationAvatarFace
          conversation={conversation}
          viewerMembershipId={viewerMembershipId}
          className="h-9 w-9"
        />
        <div className="min-w-0 flex-1">
          <div className="flex min-w-0 items-center gap-1.5">
            {conversation.pinned ? (
              <Pin
                className="h-3.5 w-3.5 shrink-0 text-[#4c8543]"
                strokeWidth={2.5}
                aria-label="Conversation épinglée"
              />
            ) : null}
            <h3 className="truncate text-sm font-semibold leading-tight text-[#1a1a1a]">{title}</h3>
          </div>
          <p
            className={cn(
              'truncate text-[13px] leading-tight',
              isUnread ? 'font-medium text-[#1a1a1a]' : 'text-[#7D7B75]',
            )}
          >
            {preview}
          </p>
        </div>
        <div className="flex shrink-0 flex-col items-end gap-1 self-start pt-0.5">
          <div className="flex items-center gap-1">
            <span
              className={cn(
                'text-[11px] leading-none',
                isUnread ? 'text-[#4c8543]' : 'text-[#888]',
              )}
            >
              {formatChatRelativeTime(conversation.last_message_at)}
            </span>
            {actionsMode === 'popover' && actionHandlers && onActionsOpenChange ? (
              <ChatConversationActionsPopover
                conversation={conversation}
                open={actionsOpen}
                isPending={actionsPending}
                errorMessage={actionsErrorMessage}
                onOpenChange={onActionsOpenChange}
                title={title}
                {...actionHandlers}
              />
            ) : (
              <button
                type="button"
                className="flex h-7 w-7 items-center justify-center rounded-full text-[#7D7B75] outline-none hover:bg-[#F5F4F0] focus-visible:ring-2 focus-visible:ring-[#114660]/30"
                aria-label={`Actions pour ${title}`}
                onClick={handleActionsClick}
              >
                <MoreHorizontal className="h-4 w-4" strokeWidth={2.25} />
              </button>
            )}
          </div>
          {unreadCount > 0 ? (
            <span
              className="inline-flex min-h-[18px] min-w-[18px] items-center justify-center rounded-full bg-[#4c8543] px-1 text-[11px] font-semibold leading-none text-white"
              aria-label={getUnreadCountAriaLabel(unreadCount)}
            >
              {formatUnreadBadgeCount(unreadCount)}
            </span>
          ) : (
            <span className="h-[18px] min-w-[18px]" aria-hidden="true" />
          )}
        </div>
      </div>
    </article>
  )
}
