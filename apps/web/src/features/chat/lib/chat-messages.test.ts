import { describe, expect, it } from 'vitest'

import { appendUniqueServerMessage, mergeServerAndLocalMessages } from './chat-messages'
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
})
