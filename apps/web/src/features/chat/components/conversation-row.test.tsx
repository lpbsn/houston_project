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

  it('renders dm avatar with teal background and compact card sizing', () => {
    const { container } = renderRow(buildConversation())

    const card = container.querySelector('article')
    expect(card?.className).toContain('py-2')
    expect(card?.className).toContain('px-3')
    expect(card?.className).toContain('rounded-[22px]')

    const avatar = container.querySelector('.h-9.w-9')
    expect(avatar?.className).toContain('bg-[#3A7A96]')
    expect(avatar?.textContent).toBe('SM')
  })

  it('renders group avatar with navy background and users icon', () => {
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

    const avatar = container.querySelector('.h-9.w-9')
    expect(avatar?.className).toContain('bg-[#114660]')
    expect(container.querySelector('.lucide-users')).toBeTruthy()
  })

  it('applies unread styling for border, time, preview, and numeric badge', () => {
    const { container } = renderRow(
      buildConversation({ unread: true, unread_count: 3 }),
    )

    const card = container.querySelector('article')
    expect(card?.className).toContain('border-[#4c8543]/35')

    const time = container.querySelector('.text-\\[\\#4c8543\\]')
    expect(time).toBeTruthy()

    const preview = container.querySelector('p')
    expect(preview?.className).toContain('font-medium')
    expect(preview?.className).toContain('text-[#1a1a1a]')

    expect(screen.getByText('3')).toBeTruthy()
    expect(screen.getByLabelText('3 messages non lus')).toBeTruthy()
  })

  it('caps badge display at 99+ while keeping the real count in aria-label', () => {
    renderRow(buildConversation({ unread: true, unread_count: 150 }))

    expect(screen.getByText('99+')).toBeTruthy()
    expect(screen.getByLabelText('150 messages non lus')).toBeTruthy()
  })

  it('keeps read styling muted without unread badge', () => {
    const { container } = renderRow(buildConversation({ unread: false, unread_count: 0 }))

    const card = container.querySelector('article')
    expect(card?.className).toContain('border-[#E8E6DF]')
    expect(card?.className).not.toContain('border-[#4c8543]/35')

    const preview = container.querySelector('p')
    expect(preview?.className).toContain('text-[#7D7B75]')
    expect(screen.queryByLabelText(/messages non lus/)).toBeNull()
  })
})
