// @vitest-environment jsdom

import { QueryClient } from '@tanstack/react-query'
import { describe, expect, it, vi } from 'vitest'

import { chatQueryKeys } from '../api'
import { purgeConversationClientState } from './purge-conversation-client-state'

describe('purgeConversationClientState', () => {
  it('removes conversation from list, detail, messages, and local messages', () => {
    const queryClient = new QueryClient()
    const establishmentId = 'est-1'
    const conversationId = 'conv-1'
    const clearLocalMessages = vi.fn()

    queryClient.setQueryData(chatQueryKeys.conversations(establishmentId), {
      items: [
        {
          id: conversationId,
          type: 'dm',
          title: '',
          created_at: '2026-06-01T09:00:00.000Z',
          unread: false,
          unread_count: 0,
          last_message_at: null,
          last_message_preview: null,
          participants: [],
          pinned: false,
          can_delete: false,
        },
        {
          id: 'conv-2',
          type: 'dm',
          title: '',
          created_at: '2026-06-01T09:00:00.000Z',
          unread: false,
          unread_count: 0,
          last_message_at: null,
          last_message_preview: null,
          participants: [],
          pinned: false,
          can_delete: false,
        },
      ],
    })
    queryClient.setQueryData(chatQueryKeys.conversation(establishmentId, conversationId), {
      id: conversationId,
    })
    queryClient.setQueryData(chatQueryKeys.messages(establishmentId, conversationId), {
      pages: [],
      pageParams: [],
    })

    purgeConversationClientState(queryClient, {
      establishmentId,
      conversationId,
      clearLocalMessages,
    })

    expect(queryClient.getQueryData(chatQueryKeys.conversations(establishmentId))).toEqual({
      items: [
        {
          id: 'conv-2',
          type: 'dm',
          title: '',
          created_at: '2026-06-01T09:00:00.000Z',
          unread: false,
          unread_count: 0,
          last_message_at: null,
          last_message_preview: null,
          participants: [],
          pinned: false,
          can_delete: false,
        },
      ],
    })
    expect(
      queryClient.getQueryData(chatQueryKeys.conversation(establishmentId, conversationId)),
    ).toBeUndefined()
    expect(
      queryClient.getQueryData(chatQueryKeys.messages(establishmentId, conversationId)),
    ).toBeUndefined()
    expect(clearLocalMessages).toHaveBeenCalledWith(conversationId)
  })
})
