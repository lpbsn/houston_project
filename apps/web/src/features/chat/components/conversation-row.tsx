import type { KeyboardEvent } from 'react'

import { getDisplayNameInitials } from '@/features/actions/lib/action-display'
import { terrainFeedInteractiveCardClassName } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

import {
  formatChatRelativeTime,
  getConversationTitle,
} from '../lib/chat-display'
import type { ChatConversationListItem } from '../types'

type ConversationRowProps = {
  conversation: ChatConversationListItem
  viewerMembershipId: string | null
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

export function ConversationRow({ conversation, viewerMembershipId, onSelect }: ConversationRowProps) {
  const title = getConversationTitle(conversation, viewerMembershipId)
  const preview = conversation.last_message_preview?.body?.trim() || 'Aucun message'
  const peer = conversation.participants.find(
    (participant) => participant.membership_id !== viewerMembershipId,
  )
  const initials = getDisplayNameInitials(peer?.display_name || title)

  return (
    <article
      className={terrainFeedInteractiveCardClassName('bg-white')}
      onClick={() => onSelect(conversation.id)}
      onKeyDown={(event) => handleRowKeyDown(event, onSelect, conversation.id)}
      role="button"
      tabIndex={0}
    >
      <div className="flex items-start gap-3">
        <div
          className={cn(
            'flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-[#EEF2FF] text-sm font-semibold text-[#1B4FD8]',
          )}
          aria-hidden="true"
        >
          {initials}
        </div>
        <div className="min-w-0 flex-1">
          <div className="mb-1 flex items-start justify-between gap-2">
            <h3 className="truncate text-sm font-semibold text-[#1a1a1a]">{title}</h3>
            <span className="shrink-0 text-[11px] text-[#888]">
              {formatChatRelativeTime(conversation.last_message_at)}
            </span>
          </div>
          <div className="flex items-center justify-between gap-2">
            <p className="truncate text-sm text-[#7D7B75]">{preview}</p>
            {conversation.unread ? (
              <span className="inline-flex h-2.5 w-2.5 shrink-0 rounded-full bg-[#1B4FD8]" />
            ) : null}
          </div>
        </div>
      </div>
    </article>
  )
}
