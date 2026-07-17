// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { ChatConversationListItem } from '../types'
import {
  collectOverflowYScrollElements,
  expectSinglePageScrollZone,
} from '@/lib/terrain-scroll-layout'

import { ChatPage } from './chat-page'

const statusQueryMock = vi.fn()
const conversationsQueryMock = vi.fn()

function buildConversation(
  id: string,
  type: 'dm' | 'group',
  options: {
    title?: string
    peerDisplayName?: string
    last_message_at?: string
  } = {},
): ChatConversationListItem {
  const peerDisplayName = options.peerDisplayName ?? 'Bob Martin'

  return {
    id,
    type,
    title: options.title ?? '',
    unread: false,
    unread_count: 0,
    last_message_at: options.last_message_at ?? '2026-06-13T12:00:00Z',
    last_message_preview: null,
    participants:
      type === 'dm'
        ? [
            {
              membership_id: 'mbr-viewer',
              user_id: 'user-viewer',
              display_name: 'Alice',
              role: 'staff',
              participant_role: 'member',
            },
            {
              membership_id: `mbr-peer-${id}`,
              user_id: `user-peer-${id}`,
              display_name: peerDisplayName,
              role: 'manager',
              participant_role: 'member',
            },
          ]
        : [
            {
              membership_id: 'mbr-viewer',
              user_id: 'user-viewer',
              display_name: 'Alice',
              role: 'staff',
              participant_role: 'member',
            },
            {
              membership_id: `mbr-member-${id}`,
              user_id: `user-member-${id}`,
              display_name: 'Claire Dupont',
              role: 'staff',
              participant_role: 'member',
            },
          ],
    pinned: false,
    can_delete: false,
  }
}

function buildStatusQueryState(overrides: Record<string, unknown> = {}) {
  return {
    isLoading: false,
    isError: false,
    data: {
      can_access: true,
      chat_enabled: true,
      can_create_dm: true,
      can_create_group: true,
      can_manage_settings: false,
    },
    ...overrides,
  }
}

function buildConversationsQueryState(overrides: Record<string, unknown> = {}) {
  return {
    isLoading: false,
    isError: false,
    isSuccess: true,
    data: { items: [] as ChatConversationListItem[] },
    ...overrides,
  }
}

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

function idleMutationMock() {
  return {
    isPending: false,
    mutateAsync: vi.fn(),
    reset: vi.fn(),
  }
}

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
  usePinConversationMutation: () => idleMutationMock(),
  useUnpinConversationMutation: () => idleMutationMock(),
  useHideDmMutation: () => idleMutationMock(),
  useLeaveGroupMutation: () => idleMutationMock(),
  useDeleteGroupMutation: () => idleMutationMock(),
}))

vi.mock('../components/chat-realtime-provider', () => ({
  useOptionalChatRealtime: () => ({
    connectionStatus: 'reconnecting',
    clearLocalMessagesForConversation: () => undefined,
  }),
}))

function renderChatPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })

  return render(
    createElement(
      QueryClientProvider,
      { client: queryClient },
      createElement(ChatPage, {
        onOpenConversation: () => undefined,
      }),
    ),
  )
}

describe('ChatPage flat conversation list', () => {
  beforeEach(() => {
    statusQueryMock.mockReturnValue(buildStatusQueryState())
    conversationsQueryMock.mockReturnValue(buildConversationsQueryState())
  })

  afterEach(() => {
    cleanup()
  })

  it('renders mixed conversations in API order without sections', () => {
    conversationsQueryMock.mockReturnValue(
      buildConversationsQueryState({
        data: {
          items: [
            buildConversation('conv-group', 'group', {
              title: 'Équipe cuisine',
              last_message_at: '2026-06-13T14:00:00Z',
            }),
            buildConversation('conv-dm', 'dm', {
              last_message_at: '2026-06-13T12:00:00Z',
            }),
          ],
        },
      }),
    )

    renderChatPage()

    expect(screen.queryByText('Messages directs')).toBeNull()
    expect(screen.queryByText('Groupes')).toBeNull()
    expect(screen.getByText('Équipe cuisine')).toBeTruthy()
    expect(screen.getByText('Bob Martin')).toBeTruthy()

    const titles = screen.getAllByRole('heading', { level: 3 }).map((node) => node.textContent)
    expect(titles).toEqual(['Équipe cuisine', 'Bob Martin'])
  })

  it('filters search results in a flat list without sections', () => {
    conversationsQueryMock.mockReturnValue(
      buildConversationsQueryState({
        data: {
          items: [
            buildConversation('conv-dm', 'dm', { peerDisplayName: 'Bob Martin' }),
            buildConversation('conv-group', 'group', { title: 'Équipe cuisine' }),
          ],
        },
      }),
    )

    renderChatPage()

    fireEvent.change(screen.getByPlaceholderText('Rechercher une conversation'), {
      target: { value: 'bob' },
    })

    expect(screen.queryByText('Messages directs')).toBeNull()
    expect(screen.queryByText('Groupes')).toBeNull()
    expect(screen.getByText('Bob Martin')).toBeTruthy()
    expect(screen.queryByText('Équipe cuisine')).toBeNull()
  })

  it('shows search empty state when no conversation matches', () => {
    conversationsQueryMock.mockReturnValue(
      buildConversationsQueryState({
        data: {
          items: [buildConversation('conv-dm', 'dm')],
        },
      }),
    )

    renderChatPage()

    fireEvent.change(screen.getByPlaceholderText('Rechercher une conversation'), {
      target: { value: 'introuvable' },
    })

    expect(screen.getByText('Aucun résultat')).toBeTruthy()
    expect(screen.queryByText('Aucune conversation')).toBeNull()
  })

  it('shows global empty state when there are no conversations', () => {
    renderChatPage()

    expect(screen.getByText('Aucune conversation')).toBeTruthy()
    expect(screen.queryByText('Messages directs')).toBeNull()
    expect(screen.queryByText('Groupes')).toBeNull()
  })

  it('uses a pill search field and a single 40px create target', () => {
    renderChatPage()

    const search = screen.getByPlaceholderText('Rechercher une conversation')
    expect(search.className).toContain('h-8')
    expect(search.className).toContain('rounded-full')

    const createButton = screen.getByRole('button', { name: 'Nouvelle conversation' })
    expect(createButton.className).toContain('h-10')
    expect(createButton.className).toContain('w-10')
    expect(within(createButton).getByText('', { selector: 'span' }).className).toContain('h-8')
    expect(within(createButton).getByText('', { selector: 'span' }).className).toContain('w-8')
  })
})

describe('ChatPage scroll layout', () => {
  beforeEach(() => {
    statusQueryMock.mockReturnValue(buildStatusQueryState())
    conversationsQueryMock.mockReturnValue(buildConversationsQueryState())
  })

  afterEach(() => {
    cleanup()
  })

  function expectChatPageRoot() {
    const root = screen.getByTestId('chat-page-root')
    expect(root.className).toContain('h-full')
    expect(root.className).toContain('min-h-0')
    expect(root.className).toContain('flex-col')
    return root
  }

  it('success state uses one scroll zone and reconnect banner is outside the scroller', () => {
    conversationsQueryMock.mockReturnValue(
      buildConversationsQueryState({
        data: {
          items: [buildConversation('conv-dm', 'dm')],
        },
      }),
    )

    const { container } = renderChatPage()
    const root = expectChatPageRoot()
    const scrollArea = expectSinglePageScrollZone(container)

    expect(scrollArea.className).toContain('overflow-y-auto')
    expect(root.contains(scrollArea)).toBe(true)

    const reconnectBanner = screen.getByRole('status')
    expect(scrollArea.contains(reconnectBanner)).toBe(false)
  })

  it('loading state keeps the same page root without a parallel scroll container', () => {
    statusQueryMock.mockReturnValue(buildStatusQueryState({ isLoading: true }))

    const { container } = renderChatPage()
    expectChatPageRoot()
    expect(collectOverflowYScrollElements(container)).toHaveLength(0)
  })

  it('error state keeps the page root and a single scroll zone', () => {
    statusQueryMock.mockReturnValue(
      buildStatusQueryState({
        isError: true,
        error: new Error('status failed'),
      }),
    )

    const { container } = renderChatPage()
    expectChatPageRoot()
    expectSinglePageScrollZone(container)
  })

  it('empty state keeps the page root and a single scroll zone', () => {
    const { container } = renderChatPage()
    expectChatPageRoot()
    expectSinglePageScrollZone(container)
    expect(screen.getByText('Aucune conversation')).toBeTruthy()
  })
})
