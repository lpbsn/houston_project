// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { ConversationRow } from './conversation-row'
import type { ChatConversationListItem } from '../types'

function buildConversation(
  overrides: Partial<ChatConversationListItem> = {},
): ChatConversationListItem {
  return {
    id: 'conv-1',
    type: 'dm',
    title: '',
    created_at: '2026-06-13T16:00:00Z',
    unread: false,
    unread_count: 0,
    last_message_at: '2026-06-13T17:25:00Z',
    last_message_preview: { body: 'Dernier message', id: 'msg-1', author_membership_id: 'mbr-peer', author_display_name: 'Peer', created_at: '2026-06-13T17:25:00Z' },
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
        display_name: 'Sarah M.',
        role: 'manager',
        participant_role: 'member',
      },
    ],
    pinned: false,
    can_delete: false,
    ...overrides,
  }
}

function renderRow(conversation: ChatConversationListItem) {
  const onSelect = () => undefined
  const onOpenActions = () => undefined
  return render(
    createElement(ConversationRow, {
      conversation,
      viewerMembershipId: 'mbr-viewer',
      onSelect,
      onOpenActions,
    }),
  )
}

describe('ConversationRow', () => {
  afterEach(() => {
    cleanup()
  })

  it('renders dm initials from the peer display name', () => {
    renderRow(buildConversation())

    expect(screen.getByText('SM')).toBeTruthy()
    expect(screen.getByText('Sarah M.')).toBeTruthy()
  })

  it('renders a group conversation with a users icon', () => {
    const { container } = renderRow(
      buildConversation({
        type: 'group',
        title: 'Équipe Cuisine',
        participants: [
          {
            membership_id: 'mbr-viewer',
            user_id: 'user-viewer',
            display_name: 'Alice',
            role: 'staff',
            participant_role: 'member',
          },
        ],
      }),
    )

    expect(screen.getByText('Équipe Cuisine')).toBeTruthy()
    expect(container.querySelector('.lucide-users')).toBeTruthy()
  })

  it('exposes unread count and accessible label', () => {
    renderRow(buildConversation({ unread: true, unread_count: 3 }))

    expect(screen.getByText('3')).toBeTruthy()
    expect(screen.getByLabelText('3 messages non lus')).toBeTruthy()
  })

  it('caps badge display at 99+ while keeping the real count in aria-label', () => {
    renderRow(buildConversation({ unread: true, unread_count: 150 }))

    expect(screen.getByText('99+')).toBeTruthy()
    expect(screen.getByLabelText('150 messages non lus')).toBeTruthy()
  })

  it('hides the unread badge when the conversation is read', () => {
    renderRow(buildConversation({ unread: false, unread_count: 0 }))

    expect(screen.queryByLabelText(/messages non lus/)).toBeNull()
  })
})
