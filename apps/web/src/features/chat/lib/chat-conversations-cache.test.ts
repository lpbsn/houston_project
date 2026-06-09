import { describe, expect, it } from 'vitest'

import {
  buildLastMessagePreview,
  patchConversationsOnMessageCreated,
  shouldMarkConversationUnread,
} from './chat-conversations-cache'
import type { ChatConversationListItem, ChatMessage } from '../types'

const sampleConversation = (
  overrides: Partial<ChatConversationListItem> = {},
): ChatConversationListItem => ({
  id: 'conv-1',
  type: 'dm',
  title: '',
  unread: false,
  last_message_at: '2026-06-01T10:00:00.000Z',
  last_message_preview: null,
  participants: [],
  ...overrides,
})

const sampleMessage = (overrides: Partial<ChatMessage> = {}): ChatMessage => ({
  id: 'msg-1',
  author_membership_id: 'mbr-peer',
  author_display_name: 'Bob',
  body: 'Hello',
  client_message_id: 'client-1',
  created_at: '2026-06-09T12:00:00.000Z',
  ...overrides,
})

describe('chat-conversations-cache', () => {
  it('marks inactive conversation unread when author is another member', () => {
    expect(
      shouldMarkConversationUnread({
        authorMembershipId: 'mbr-peer',
        viewerMembershipId: 'mbr-viewer',
        conversationId: 'conv-1',
        activeConversationId: null,
      }),
    ).toBe(true)
  })

  it('does not mark active conversation unread', () => {
    expect(
      shouldMarkConversationUnread({
        authorMembershipId: 'mbr-peer',
        viewerMembershipId: 'mbr-viewer',
        conversationId: 'conv-1',
        activeConversationId: 'conv-1',
      }),
    ).toBe(false)
  })

  it('does not mark unread for own messages', () => {
    expect(
      shouldMarkConversationUnread({
        authorMembershipId: 'mbr-viewer',
        viewerMembershipId: 'mbr-viewer',
        conversationId: 'conv-1',
        activeConversationId: null,
      }),
    ).toBe(false)
  })

  it('patches preview, unread, and re-sorts conversations', () => {
    const message = sampleMessage()
    const result = patchConversationsOnMessageCreated(
      {
        items: [
          sampleConversation({ id: 'conv-2', last_message_at: '2026-06-08T10:00:00.000Z' }),
          sampleConversation({ id: 'conv-1' }),
        ],
      },
      {
        conversationId: 'conv-1',
        message,
        viewerMembershipId: 'mbr-viewer',
        activeConversationId: null,
      },
    )

    expect(result?.items[0]?.id).toBe('conv-1')
    expect(result?.items[0]?.unread).toBe(true)
    expect(result?.items[0]?.last_message_preview).toEqual(buildLastMessagePreview(message))
    expect(result?.items[0]?.last_message_at).toBe(message.created_at)
  })

  it('keeps active conversation unread false when another user sends a message', () => {
    const result = patchConversationsOnMessageCreated(
      { items: [sampleConversation()] },
      {
        conversationId: 'conv-1',
        message: sampleMessage(),
        viewerMembershipId: 'mbr-viewer',
        activeConversationId: 'conv-1',
      },
    )

    expect(result?.items[0]?.unread).toBe(false)
  })

  it('does not expose read receipt fields in preview helper', () => {
    const preview = buildLastMessagePreview(sampleMessage())
    expect(Object.keys(preview).sort()).toEqual(
      [
        'author_display_name',
        'author_membership_id',
        'body',
        'created_at',
        'id',
      ].sort(),
    )
  })
})
