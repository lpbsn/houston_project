import { describe, expect, it } from 'vitest'

import {
  filterConversationsByQuery,
  getConversationTitle,
  hasUnreadConversations,
} from './chat-display'
import type { ChatConversationListItem } from '../types'

const sampleConversation = (
  overrides: Partial<ChatConversationListItem> = {},
): ChatConversationListItem => ({
  id: 'conv-1',
  type: 'dm',
  title: '',
  unread: false,
  last_message_at: null,
  last_message_preview: null,
  participants: [
    {
      membership_id: 'mbr-viewer',
      user_id: 'user-viewer',
      display_name: 'Alice',
      role: 'staff',
      participant_role: 'member',
    },
    {
      membership_id: 'mbr-peer',
      user_id: 'user-peer',
      display_name: 'Bob Martin',
      role: 'manager',
      participant_role: 'member',
    },
  ],
  ...overrides,
})

describe('chat-display', () => {
  it('derives dm title from peer display name', () => {
    expect(getConversationTitle(sampleConversation(), 'mbr-viewer')).toBe('Bob Martin')
  })

  it('filters conversations by participant name', () => {
    const conversations = [
      sampleConversation(),
      sampleConversation({
        id: 'conv-2',
        participants: [
          {
            membership_id: 'mbr-viewer',
            user_id: 'user-viewer',
            display_name: 'Alice',
            role: 'staff',
            participant_role: 'member',
          },
          {
            membership_id: 'mbr-other',
            user_id: 'user-other',
            display_name: 'Claire Dupont',
            role: 'staff',
            participant_role: 'member',
          },
        ],
      }),
    ]

    expect(filterConversationsByQuery(conversations, 'claire', 'mbr-viewer')).toHaveLength(1)
  })

  it('detects unread conversations', () => {
    expect(hasUnreadConversations([sampleConversation({ unread: true })])).toBe(true)
    expect(hasUnreadConversations([sampleConversation({ unread: false })])).toBe(false)
  })
})
