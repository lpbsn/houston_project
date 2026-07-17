import type { KeyboardEvent, MouseEvent } from 'react'
import { MoreHorizontal, Pin, Users } from 'lucide-react'

import { getDisplayNameInitials } from '@/lib/display-names'
import { terrainBrandAction, terrainFeedAvatar } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

import {
  formatChatRelativeTime,
  formatUnreadBadgeCount,
  getConversationTitle,
  getUnreadCountAriaLabel,
} from '../lib/chat-display'
import type { ChatConversationListItem } from '../types'

type ConversationRowProps = {
  conversation: ChatConversationListItem
  viewerMembershipId: string | null
  onSelect: (conversationId: string) => void
  onOpenActions: (conversation: ChatConversationListItem) => void
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

export function ConversationRow({
  conversation,
  viewerMembershipId,
  onSelect,
  onOpenActions,
}: ConversationRowProps) {
  const title = getConversationTitle(conversation, viewerMembershipId)
  const preview = conversation.last_message_preview?.body?.trim() || 'Aucun message'
  const isGroup = conversation.type === 'group'
  const peer = conversation.participants.find(
    (participant) => participant.membership_id !== viewerMembershipId,
  )
  const initials = getDisplayNameInitials(peer?.display_name || title)
  const isUnread = conversation.unread
  const unreadCount = conversation.unread_count

  function handleActionsClick(event: MouseEvent<HTMLButtonElement>) {
    event.preventDefault()
    event.stopPropagation()
    onOpenActions(conversation)
  }

  return (
    <article
      className={cn(
        'cursor-pointer rounded-[22px] border bg-white py-2 px-3 transition',
        isUnread ? 'border-[#4c8543]/35' : 'border-[#E8E6DF]',
      )}
      onClick={() => onSelect(conversation.id)}
      onKeyDown={(event) => handleRowKeyDown(event, onSelect, conversation.id)}
      role="button"
      tabIndex={0}
    >
      <div className="flex items-center gap-2.5">
        <div
          className={cn(
            'flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-xs font-semibold',
            isGroup ? cn(terrainBrandAction.bg, 'text-white') : terrainFeedAvatar,
          )}
          aria-hidden="true"
        >
          {isGroup ? <Users className="h-4 w-4" strokeWidth={2.25} /> : initials}
        </div>
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
            <button
              type="button"
              className="flex h-7 w-7 items-center justify-center rounded-full text-[#7D7B75] outline-none hover:bg-[#F5F4F0] focus-visible:ring-2 focus-visible:ring-[#114660]/30"
              aria-label={`Actions pour ${title}`}
              onClick={handleActionsClick}
            >
              <MoreHorizontal className="h-4 w-4" strokeWidth={2.25} />
            </button>
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
