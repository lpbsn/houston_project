import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, expect, it, vi } from 'vitest'

import { ChatPage } from './chat-page'

vi.mock('@/app/auth-provider', () => ({
  useAuth: () => ({
    bootstrap: {
      active_membership: {
        id: 'mbr-viewer',
        establishment_id: 'est-1',
      },
      user: {
        username: 'viewer',
      },
    },
  }),
}))

const statusQueryMock = vi.fn(() => ({
  isLoading: false,
  isError: false,
  data: {
    can_access: true,
    chat_enabled: true,
    can_create_dm: true,
    can_create_group: false,
    can_manage_settings: false,
  },
}))

const conversationsQueryMock = vi.fn(() => ({
  isLoading: false,
  isError: false,
  isSuccess: true,
  data: { items: [] },
}))

vi.mock('../hooks', () => ({
  useChatStatusQuery: () => statusQueryMock(),
  useChatConversationsQuery: () => conversationsQueryMock(),
  useEligibleChatMembershipsQuery: () => ({
    isLoading: false,
    isError: false,
    data: { items: [] },
  }),
  useCreateDmMutation: () => ({
    mutate: () => undefined,
    isPending: false,
  }),
  useCreateGroupMutation: () => ({
    mutate: () => undefined,
    isPending: false,
  }),
}))

function renderChatPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })

  return renderToStaticMarkup(
    createElement(
      QueryClientProvider,
      { client: queryClient },
      createElement(ChatPage, {
        onOpenConversation: () => undefined,
      }),
    ),
  )
}

describe('ChatPage provider safety', () => {
  it('renders without ChatRealtimeProvider and does not crash', () => {
    const markup = renderChatPage()
    expect(markup.length).toBeGreaterThan(0)
  })

  it('renders unavailable state when chat is disabled without provider', () => {
    statusQueryMock.mockReturnValueOnce({
      isLoading: false,
      isError: false,
      data: {
        can_access: false,
        chat_enabled: false,
        can_create_dm: false,
        can_create_group: false,
        can_manage_settings: false,
      },
    })

    const markup = renderChatPage()
    expect(markup).not.toContain('ConversationRow')
  })

  it('renders loading state without provider while status is loading', () => {
    statusQueryMock.mockReturnValueOnce({
      isLoading: true,
      isError: false,
      data: undefined,
    })

    const markup = renderChatPage()
    expect(markup).toContain('animate-spin')
  })
})
