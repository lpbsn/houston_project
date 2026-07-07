import { describe, expect, it } from 'vitest'

import {
  filterConversationsByQuery,
  getConversationTitle,
  groupConversationsByType,
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

describe('groupConversationsByType', () => {
  it('returns dm then group sections for mixed conversations', () => {
    const dm = sampleConversation({ id: 'conv-dm' })
    const group = sampleConversation({
      id: 'conv-group',
      type: 'group',
      title: 'Équipe cuisine',
    })

    const groups = groupConversationsByType([group, dm])

    expect(groups).toHaveLength(2)
    expect(groups[0]?.section).toBe('dm')
    expect(groups[0]?.label).toBe('Messages directs')
    expect(groups[0]?.items.map((item) => item.id)).toEqual(['conv-dm'])
    expect(groups[1]?.section).toBe('group')
    expect(groups[1]?.label).toBe('Groupes')
    expect(groups[1]?.items.map((item) => item.id)).toEqual(['conv-group'])
  })

  it('preserves input order within each section', () => {
    const firstDm = sampleConversation({ id: 'conv-dm-1' })
    const secondDm = sampleConversation({
      id: 'conv-dm-2',
      participants: [
        {
          membership_id: 'mbr-viewer',
          user_id: 'user-viewer',
          display_name: 'Alice',
          role: 'staff',
          participant_role: 'member',
        },
        {
          membership_id: 'mbr-peer-2',
          user_id: 'user-peer-2',
          display_name: 'Claire Dupont',
          role: 'staff',
          participant_role: 'member',
        },
      ],
    })

    const groups = groupConversationsByType([firstDm, secondDm])

    expect(groups).toHaveLength(1)
    expect(groups[0]?.items.map((item) => item.id)).toEqual(['conv-dm-1', 'conv-dm-2'])
  })

  it('omits empty sections', () => {
    const groups = groupConversationsByType([sampleConversation({ id: 'conv-dm' })])

    expect(groups).toHaveLength(1)
    expect(groups[0]?.section).toBe('dm')
    expect(groups[0]?.label).toBe('Messages directs')
  })

  it('returns an empty list when there are no conversations', () => {
    expect(groupConversationsByType([])).toEqual([])
  })
})
