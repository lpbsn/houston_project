import { describe, expect, it } from 'vitest'

import {
  filterConversationsByQuery,
  formatUnreadBadgeCount,
  getConversationTitle,
  getUnreadCountAriaLabel,
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
  unread_count: 0,
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
  pinned: false,
  can_delete: false,
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

  it('preserves API order when filtering conversations', () => {
    const group = sampleConversation({
      id: 'conv-group',
      type: 'group',
      title: 'Équipe cuisine',
    })
    const dm = sampleConversation({ id: 'conv-dm' })

    expect(filterConversationsByQuery([group, dm], '', 'mbr-viewer').map((item) => item.id)).toEqual([
      'conv-group',
      'conv-dm',
    ])
  })

  it('detects unread conversations', () => {
    expect(hasUnreadConversations([sampleConversation({ unread: true })])).toBe(true)
    expect(hasUnreadConversations([sampleConversation({ unread: false })])).toBe(false)
  })

  it('formats unread badge count with 99+ cap for display only', () => {
    expect(formatUnreadBadgeCount(3)).toBe('3')
    expect(formatUnreadBadgeCount(99)).toBe('99')
    expect(formatUnreadBadgeCount(150)).toBe('99+')
  })

  it('keeps the real unread count in aria labels', () => {
    expect(getUnreadCountAriaLabel(1)).toBe('1 message non lu')
    expect(getUnreadCountAriaLabel(3)).toBe('3 messages non lus')
    expect(getUnreadCountAriaLabel(150)).toBe('150 messages non lus')
  })
})
