import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { BottomMobileNav } from '@/components/layout/bottom-mobile-nav'

import { chatQueryKeys } from './api'
import { ChatRealtimeProvider } from './components/chat-realtime-provider'
import { hasUnreadConversations } from './lib/chat-display'
import type { ChatConversationListItem, ChatMessage, ChatWsMessageCreatedEvent } from './types'

const ESTABLISHMENT_ID = 'est-1'
const VIEWER_MEMBERSHIP_ID = 'mbr-viewer'

let capturedOnMessageCreated: ((event: ChatWsMessageCreatedEvent) => void) | undefined

vi.mock('./hooks/use-chat-websocket', () => ({
  useChatWebSocket: (options: {
    onMessageCreated?: (event: ChatWsMessageCreatedEvent) => void
  }) => {
    capturedOnMessageCreated = options.onMessageCreated
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

vi.mock('./hooks', async (importOriginal) => {
  const actual = await importOriginal<typeof import('./hooks')>()
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
  last_message_at: '2026-06-01T10:00:00.000Z',
  last_message_preview: null,
  participants: [],
})

const incomingMessage = (): ChatMessage => ({
  id: 'msg-2',
  author_membership_id: 'mbr-peer',
  author_display_name: 'Peer',
  body: 'New message',
  client_message_id: 'client-2',
  created_at: '2026-06-09T15:00:00.000Z',
})

function TerrainUnreadHarness({ queryClient }: { queryClient: QueryClient }) {
  const conversations =
    queryClient.getQueryData<{ items: ChatConversationListItem[] }>(
      chatQueryKeys.conversations(ESTABLISHMENT_ID),
    )?.items ?? []
  const chatHasUnread = conversations.some((item) => item.unread)

  return (
    <QueryClientProvider client={queryClient}>
      <ChatRealtimeProvider establishmentId={ESTABLISHMENT_ID} activeConversationId={null}>
        <div data-terrain-route="/signals">Signals stub</div>
        <BottomMobileNav
          activePath="/signals"
          navigate={() => undefined}
          showChat={true}
          chatHasUnread={chatHasUnread}
        />
      </ChatRealtimeProvider>
    </QueryClientProvider>
  )
}

describe('chat terrain unread integration', () => {
  beforeEach(() => {
    capturedOnMessageCreated = undefined
  })

  it('updates conversations cache and bottom nav dot on message.created while off Chat route', () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })

    queryClient.setQueryData(chatQueryKeys.conversations(ESTABLISHMENT_ID), {
      items: [sampleConversation()],
    })

    renderToStaticMarkup(createElement(TerrainUnreadHarness, { queryClient }))

    expect(capturedOnMessageCreated).toBeTypeOf('function')

    const message = incomingMessage()
    capturedOnMessageCreated?.({
      type: 'message.created',
      conversation_id: 'conv-1',
      message,
    })

    const patched = queryClient.getQueryData<{ items: ChatConversationListItem[] }>(
      chatQueryKeys.conversations(ESTABLISHMENT_ID),
    )

    expect(patched?.items[0]?.unread).toBe(true)
    expect(patched?.items[0]?.last_message_preview?.body).toBe('New message')
    expect(hasUnreadConversations(patched?.items ?? [])).toBe(true)

    const navMarkup = renderToStaticMarkup(
      createElement(BottomMobileNav, {
        activePath: '/signals',
        navigate: () => undefined,
        showChat: true,
        chatHasUnread: hasUnreadConversations(patched?.items ?? []),
      }),
    )

    expect(navMarkup).toContain('rounded-full')
  })
})
