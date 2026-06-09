import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { chatQueryKeys } from '../api'
import type { ChatConversationListItem, ChatWsMessageCreatedEvent } from '../types'
import { ChatRealtimeProvider } from './chat-realtime-provider'

const ESTABLISHMENT_ID = 'est-1'
const VIEWER_MEMBERSHIP_ID = 'mbr-viewer'

let capturedOnMessageCreated: ((event: ChatWsMessageCreatedEvent) => void) | undefined
let capturedOnReconnect: (() => void) | undefined

vi.mock('../hooks/use-chat-websocket', () => ({
  useChatWebSocket: (options: {
    onMessageCreated?: (event: ChatWsMessageCreatedEvent) => void
    onReconnect?: () => void
  }) => {
    capturedOnMessageCreated = options.onMessageCreated
    capturedOnReconnect = options.onReconnect
    return {
      connectionStatus: 'connected',
      sendMessage: () => true,
      reconnect: vi.fn(),
    }
  },
}))

vi.mock('@/app/auth-provider', () => ({
  useAuth: () => ({
    bootstrap: {
      active_membership: {
        id: VIEWER_MEMBERSHIP_ID,
        establishment_id: ESTABLISHMENT_ID,
      },
    },
  }),
}))

vi.mock('../hooks', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../hooks')>()
  return {
    ...actual,
    useChatStatusQuery: () => ({
      data: {
        can_access: true,
        chat_enabled: true,
        can_create_dm: true,
        can_create_group: false,
        can_manage_settings: false,
      },
    }),
  }
})

const sampleConversation = (): ChatConversationListItem => ({
  id: 'conv-1',
  type: 'dm',
  title: '',
  unread: false,
  last_message_at: null,
  last_message_preview: null,
  participants: [],
})

describe('ChatRealtimeProvider', () => {
  beforeEach(() => {
    capturedOnMessageCreated = undefined
    capturedOnReconnect = undefined
  })

  it('patches conversations cache on message.created', () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

    queryClient.setQueryData(chatQueryKeys.conversations(ESTABLISHMENT_ID), {
      items: [sampleConversation()],
    })

    renderToStaticMarkup(
      createElement(
        QueryClientProvider,
        { client: queryClient },
        createElement(ChatRealtimeProvider, {
          establishmentId: ESTABLISHMENT_ID,
          activeConversationId: null,
        }),
      ),
    )

    capturedOnMessageCreated?.({
      type: 'message.created',
      conversation_id: 'conv-1',
      message: {
        id: 'msg-1',
        author_membership_id: 'mbr-peer',
        author_display_name: 'Peer',
        body: 'Ping',
        client_message_id: 'client-1',
        created_at: '2026-06-09T16:00:00.000Z',
      },
    })

    const patched = queryClient.getQueryData<{ items: ChatConversationListItem[] }>(
      chatQueryKeys.conversations(ESTABLISHMENT_ID),
    )

    expect(patched?.items[0]?.unread).toBe(true)
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: chatQueryKeys.conversations(ESTABLISHMENT_ID),
    })
  })

  it('invalidates conversations and active messages on reconnect', () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

    renderToStaticMarkup(
      createElement(
        QueryClientProvider,
        { client: queryClient },
        createElement(ChatRealtimeProvider, {
          establishmentId: ESTABLISHMENT_ID,
          activeConversationId: 'conv-active',
        }),
      ),
    )

    capturedOnReconnect?.()

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: chatQueryKeys.conversations(ESTABLISHMENT_ID),
    })
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: chatQueryKeys.messages(ESTABLISHMENT_ID, 'conv-active'),
    })
  })
})
