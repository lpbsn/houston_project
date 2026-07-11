import { describe, expect, it } from 'vitest'

import {
  appendUniqueServerMessage,
  flattenChatMessagePages,
  mergeServerAndLocalMessages,
} from './chat-messages'
import type { ChatMessage, LocalChatMessage } from '../types'

const serverMessage = (overrides: Partial<ChatMessage> = {}): ChatMessage => ({
  id: 'msg-1',
  author_membership_id: 'mbr-1',
  author_display_name: 'Alice',
  body: 'Hello',
  client_message_id: 'client-1',
  created_at: '2026-06-09T10:00:00.000Z',
  ...overrides,
})

const localMessage = (overrides: Partial<LocalChatMessage> = {}): LocalChatMessage => ({
  clientMessageId: 'client-2',
  conversationId: 'conv-1',
  body: 'Pending',
  status: 'pending',
  createdAt: '2026-06-09T10:01:00.000Z',
  authorMembershipId: 'mbr-1',
  authorDisplayName: 'Alice',
  ...overrides,
})

describe('chat-messages', () => {
  it('merges pending local messages with server history', () => {
    const merged = mergeServerAndLocalMessages(
      [serverMessage()],
      [localMessage()],
      'conv-1',
    )

    expect(merged).toHaveLength(2)
    expect(merged[1]?.kind).toBe('local')
  })

  it('drops local messages once server echoes the same client id', () => {
    const merged = mergeServerAndLocalMessages(
      [serverMessage({ client_message_id: 'client-2' })],
      [localMessage({ status: 'pending' })],
      'conv-1',
    )

    expect(merged).toHaveLength(1)
    expect(merged[0]?.kind).toBe('server')
  })

  it('appends unique server messages in chronological order', () => {
    const first = serverMessage()
    const second = serverMessage({
      id: 'msg-2',
      client_message_id: 'client-2',
      created_at: '2026-06-09T10:02:00.000Z',
    })

    expect(appendUniqueServerMessage([first], second)).toEqual([first, second])
    expect(appendUniqueServerMessage([first], first)).toEqual([first])
  })

  it('appends a newer server message at the end when the page is out of order', () => {
    const older = serverMessage({
      id: 'msg-older',
      client_message_id: 'client-older',
      created_at: '2026-06-09T10:00:00.000Z',
    })
    const newer = serverMessage({
      id: 'msg-newer',
      client_message_id: 'client-newer',
      created_at: '2026-06-09T10:05:00.000Z',
    })
    const incoming = serverMessage({
      id: 'msg-incoming',
      client_message_id: 'client-incoming',
      created_at: '2026-06-09T10:10:00.000Z',
    })

    const result = appendUniqueServerMessage([newer, older], incoming)

    expect(result.map((message) => message.id)).toEqual([
      'msg-older',
      'msg-newer',
      'msg-incoming',
    ])
  })

  it('flattens paginated pages into global chronological order', () => {
    const recentPage = {
      items: [
        serverMessage({
          id: 'msg-51',
          client_message_id: 'client-51',
          created_at: '2026-06-09T11:00:00.000Z',
        }),
        serverMessage({
          id: 'msg-100',
          client_message_id: 'client-100',
          created_at: '2026-06-09T12:00:00.000Z',
        }),
      ],
    }
    const olderPage = {
      items: [
        serverMessage({
          id: 'msg-1',
          client_message_id: 'client-1',
          created_at: '2026-06-09T09:00:00.000Z',
        }),
        serverMessage({
          id: 'msg-50',
          client_message_id: 'client-50',
          created_at: '2026-06-09T10:30:00.000Z',
        }),
      ],
    }

    const flattened = flattenChatMessagePages([recentPage, olderPage])

    expect(flattened.map((message) => message.id)).toEqual([
      'msg-1',
      'msg-50',
      'msg-51',
      'msg-100',
    ])
  })

  it('keeps pending local messages after server history', () => {
    const merged = mergeServerAndLocalMessages(
      [
        serverMessage({
          id: 'msg-1',
          client_message_id: 'client-1',
          created_at: '2026-06-09T10:00:00.000Z',
        }),
        serverMessage({
          id: 'msg-2',
          client_message_id: 'client-2',
          created_at: '2026-06-09T10:05:00.000Z',
        }),
      ],
      [
        localMessage({
          clientMessageId: 'client-pending',
          createdAt: '2026-06-09T10:10:00.000Z',
        }),
      ],
      'conv-1',
    )

    expect(merged).toHaveLength(3)
    expect(merged[2]?.kind).toBe('local')
    expect(merged[2]?.kind === 'local' ? merged[2].message.clientMessageId : null).toBe(
      'client-pending',
    )
  })
})
