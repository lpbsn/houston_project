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
  unread_count: 0,
  last_message_at: '2026-06-01T10:00:00.000Z',
  last_message_preview: null,
  participants: [],
  pinned: false,
  can_delete: false,
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

  it('patches preview, unread_count, unread, and re-sorts conversations', () => {
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
    expect(result?.items[0]?.unread_count).toBe(1)
    expect(result?.items[0]?.unread).toBe(true)
    expect(result?.items[0]?.last_message_preview).toEqual(buildLastMessagePreview(message))
    expect(result?.items[0]?.last_message_at).toBe(message.created_at)
  })

  it('increments unread_count for subsequent inactive messages', () => {
    const firstPatch = patchConversationsOnMessageCreated(
      { items: [sampleConversation({ unread_count: 1, unread: true })] },
      {
        conversationId: 'conv-1',
        message: sampleMessage({ id: 'msg-2', created_at: '2026-06-09T13:00:00.000Z' }),
        viewerMembershipId: 'mbr-viewer',
        activeConversationId: null,
      },
    )

    expect(firstPatch?.items[0]?.unread_count).toBe(2)
    expect(firstPatch?.items[0]?.unread).toBe(true)
  })

  it('keeps active conversation unread_count unchanged when another user sends a message', () => {
    const result = patchConversationsOnMessageCreated(
      { items: [sampleConversation({ unread_count: 3, unread: true })] },
      {
        conversationId: 'conv-1',
        message: sampleMessage(),
        viewerMembershipId: 'mbr-viewer',
        activeConversationId: 'conv-1',
      },
    )

    expect(result?.items[0]?.unread_count).toBe(3)
    expect(result?.items[0]?.unread).toBe(true)
  })

  it('does not reset unread_count for own messages', () => {
    const result = patchConversationsOnMessageCreated(
      { items: [sampleConversation({ unread_count: 3, unread: true })] },
      {
        conversationId: 'conv-1',
        message: sampleMessage({ author_membership_id: 'mbr-viewer' }),
        viewerMembershipId: 'mbr-viewer',
        activeConversationId: null,
      },
    )

    expect(result?.items[0]?.unread_count).toBe(3)
    expect(result?.items[0]?.unread).toBe(true)
  })

  it('ignores duplicate websocket events for the same message id', () => {
    const message = sampleMessage()
    const current = {
      items: [
        sampleConversation({
          unread_count: 1,
          unread: true,
          last_message_preview: buildLastMessagePreview(message),
        }),
      ],
    }

    const result = patchConversationsOnMessageCreated(current, {
      conversationId: 'conv-1',
      message,
      viewerMembershipId: 'mbr-viewer',
      activeConversationId: null,
    })

    expect(result).toEqual(current)
  })

  it('ignores out-of-order message.created events with an older timestamp', () => {
    const newerPreview = buildLastMessagePreview(
      sampleMessage({ id: 'msg-2', body: 'Newer', created_at: '2026-06-09T13:00:00.000Z' }),
    )
    const current = {
      items: [
        sampleConversation({
          id: 'conv-2',
          last_message_at: '2026-06-09T14:00:00.000Z',
          last_message_preview: buildLastMessagePreview(
            sampleMessage({ id: 'msg-other', created_at: '2026-06-09T14:00:00.000Z' }),
          ),
        }),
        sampleConversation({
          unread_count: 2,
          unread: true,
          last_message_at: '2026-06-09T13:00:00.000Z',
          last_message_preview: newerPreview,
        }),
      ],
    }

    const result = patchConversationsOnMessageCreated(current, {
      conversationId: 'conv-1',
      message: sampleMessage({ id: 'msg-1', created_at: '2026-06-09T12:00:00.000Z' }),
      viewerMembershipId: 'mbr-viewer',
      activeConversationId: null,
    })

    expect(result).toEqual(current)
    expect(result?.items.map((item) => item.id)).toEqual(['conv-2', 'conv-1'])
    expect(result?.items[1]?.unread_count).toBe(2)
    expect(result?.items[1]?.last_message_preview).toEqual(newerPreview)
    expect(result?.items[1]?.last_message_at).toBe('2026-06-09T13:00:00.000Z')
  })

  it('ignores out-of-order message.created events with the same timestamp and lower id', () => {
    const timestamp = '2026-06-09T13:00:00.000Z'
    const cachedPreview = buildLastMessagePreview(
      sampleMessage({ id: 'msg-b', body: 'Cached', created_at: timestamp }),
    )
    const current = {
      items: [
        sampleConversation({
          id: 'conv-2',
          last_message_at: '2026-06-09T14:00:00.000Z',
          last_message_preview: buildLastMessagePreview(
            sampleMessage({ id: 'msg-other', created_at: '2026-06-09T14:00:00.000Z' }),
          ),
        }),
        sampleConversation({
          unread_count: 2,
          unread: true,
          last_message_at: timestamp,
          last_message_preview: cachedPreview,
        }),
      ],
    }

    const result = patchConversationsOnMessageCreated(current, {
      conversationId: 'conv-1',
      message: sampleMessage({ id: 'msg-a', body: 'Older tie', created_at: timestamp }),
      viewerMembershipId: 'mbr-viewer',
      activeConversationId: null,
    })

    expect(result).toEqual(current)
    expect(result?.items.map((item) => item.id)).toEqual(['conv-2', 'conv-1'])
    expect(result?.items[1]?.unread_count).toBe(2)
    expect(result?.items[1]?.last_message_preview).toEqual(cachedPreview)
    expect(result?.items[1]?.last_message_at).toBe(timestamp)
  })

  it('applies message.created events with the same timestamp and higher id', () => {
    const timestamp = '2026-06-09T13:00:00.000Z'
    const incoming = sampleMessage({ id: 'msg-b', body: 'Newer tie', created_at: timestamp })
    const current = {
      items: [
        sampleConversation({
          id: 'conv-2',
          last_message_at: '2026-06-09T14:00:00.000Z',
          last_message_preview: buildLastMessagePreview(
            sampleMessage({ id: 'msg-other', created_at: '2026-06-09T14:00:00.000Z' }),
          ),
        }),
        sampleConversation({
          unread_count: 2,
          unread: true,
          last_message_at: timestamp,
          last_message_preview: buildLastMessagePreview(
            sampleMessage({ id: 'msg-a', body: 'Cached', created_at: timestamp }),
          ),
        }),
      ],
    }

    const result = patchConversationsOnMessageCreated(current, {
      conversationId: 'conv-1',
      message: incoming,
      viewerMembershipId: 'mbr-viewer',
      activeConversationId: null,
    })

    expect(result?.items[1]?.unread_count).toBe(3)
    expect(result?.items[1]?.unread).toBe(true)
    expect(result?.items[1]?.last_message_preview).toEqual(buildLastMessagePreview(incoming))
    expect(result?.items[1]?.last_message_at).toBe(timestamp)
    expect(result?.items.map((item) => item.id)).toEqual(['conv-2', 'conv-1'])
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

  it('keeps pinned conversations before newer unpinned ones after message patch', () => {
    const result = patchConversationsOnMessageCreated(
      {
        items: [
          sampleConversation({
            id: 'pinned',
            pinned: true,
            last_message_at: '2026-06-01T10:00:00.000Z',
          }),
          sampleConversation({
            id: 'unpinned',
            pinned: false,
            last_message_at: '2026-06-01T09:00:00.000Z',
          }),
        ],
      },
      {
        conversationId: 'unpinned',
        message: sampleMessage({
          id: 'msg-new',
          created_at: '2026-06-10T12:00:00.000Z',
        }),
        viewerMembershipId: 'mbr-viewer',
        activeConversationId: null,
      },
    )

    expect(result?.items.map((item) => item.id)).toEqual(['pinned', 'unpinned'])
  })
})
