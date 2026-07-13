// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { ChatConversationDetail, ChatMessage } from '../types'

import { ChatConversationPage } from './chat-conversation-page'

const CONVERSATION_ID = 'conv-1'

const conversationDetail: ChatConversationDetail = {
  id: CONVERSATION_ID,
  type: 'dm',
  title: '',
  created_at: '2026-07-11T10:00:00.000Z',
  last_message_at: '2026-07-11T17:16:00.000Z',
  unread: false,
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
      display_name: 'Franky Super',
      role: 'manager',
      participant_role: 'member',
    },
  ],
  can_manage: false,
  can_delete: false,
}

const serverMessage: ChatMessage = {
  id: 'msg-1',
  author_membership_id: 'mbr-viewer',
  author_display_name: 'Alice',
  body: 'wd',
  client_message_id: 'client-1',
  created_at: '2026-07-11T17:16:00.000Z',
}

vi.mock('@/app/auth-provider', () => ({
  useAuth: () => ({
    bootstrap: {
      active_membership: {
        id: 'mbr-viewer',
        establishment_id: 'est-1',
      },
      user: {
        username: 'alice',
      },
    },
  }),
}))

vi.mock('../components/chat-realtime-provider', () => ({
  useOptionalChatRealtime: () => ({
    connectionStatus: 'connected',
    localMessages: [],
    sendChatMessage: () => ({ clientMessageId: 'client-local', queued: true }),
    retryFailedMessage: () => false,
  }),
}))

vi.mock('../hooks/use-chat-conversation-presence', () => ({
  useChatConversationPresence: vi.fn(),
}))

function buildDetailQueryState() {
  return {
    isLoading: false,
    isError: false,
    isSuccess: true,
    data: conversationDetail,
  }
}

function buildMessagesQueryState() {
  return {
    isLoading: false,
    isError: false,
    isSuccess: true,
    hasNextPage: false,
    isFetchingNextPage: false,
    fetchNextPage: vi.fn(),
    data: {
      pages: [{ items: [serverMessage], has_more: false }],
      pageParams: [undefined],
    },
  }
}

const detailQueryMock = vi.fn(buildDetailQueryState)
const messagesQueryMock = vi.fn(buildMessagesQueryState)

vi.mock('../hooks', () => ({
  useChatConversationDetailQuery: () => detailQueryMock(),
  useChatMessagesInfiniteQuery: () => messagesQueryMock(),
  useMarkConversationSeenMutation: vi.fn(() => ({
    mutate: vi.fn(),
  })),
}))

function renderConversationPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })

  return render(
    createElement(
      QueryClientProvider,
      { client: queryClient },
      createElement(ChatConversationPage, { conversationId: CONVERSATION_ID }),
    ),
  )
}

describe('ChatConversationPage', () => {
  const scrollTo = vi.fn()

  beforeEach(() => {
    scrollTo.mockClear()
    Element.prototype.scrollTo = scrollTo
    Object.defineProperty(HTMLElement.prototype, 'scrollHeight', {
      configurable: true,
      get() {
        return 480
      },
    })
    window.matchMedia = vi.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })) as typeof window.matchMedia
  })

  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
    vi.restoreAllMocks()
  })

  it('anchors the message list to the bottom of the scroll area', () => {
    detailQueryMock.mockReturnValue(buildDetailQueryState())
    messagesQueryMock.mockReturnValue(buildMessagesQueryState())

    const { container } = renderConversationPage()

    expect(screen.getByText('wd')).toBeTruthy()
    expect(screen.getByText('Franky Super')).toBeTruthy()

    const anchorWrapper = container.querySelector('.min-h-full.justify-end')
    expect(anchorWrapper).not.toBeNull()
    expect(anchorWrapper?.textContent).toContain('wd')
  })

  it('scrolls the message container to the bottom when messages update', () => {
    detailQueryMock.mockReturnValue(buildDetailQueryState())
    messagesQueryMock.mockReturnValue(buildMessagesQueryState())

    renderConversationPage()

    expect(scrollTo).toHaveBeenCalledWith({
      top: 480,
      behavior: 'smooth',
    })
  })
})
