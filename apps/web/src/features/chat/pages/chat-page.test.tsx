// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
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
    created_at: '2026-06-13T11:00:00Z',
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

const runtimeState = vi.hoisted(() => ({ current: 'web' as 'web' | 'native' }))
const lgViewportState = vi.hoisted(() => ({ current: false }))

vi.mock('@/lib/runtime', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/runtime')>()
  return {
    ...actual,
    getAppRuntime: () => runtimeState.current,
  }
})

vi.mock('@/lib/lg-viewport', () => ({
  useLgViewport: () => lgViewportState.current,
  useXlViewport: () => false,
}))

const pinMutationState = vi.hoisted(() => ({
  isPending: false,
  error: null as unknown,
  mutateAsync: vi.fn().mockResolvedValue(undefined),
  reset: vi.fn(() => {
    pinMutationState.error = null
    pinMutationState.isPending = false
  }),
}))

const hideMutationState = vi.hoisted(() => ({
  isPending: false,
  error: null as unknown,
  mutateAsync: vi.fn().mockResolvedValue(undefined),
  reset: vi.fn(() => {
    hideMutationState.error = null
    hideMutationState.isPending = false
  }),
}))

function idleMutationMock() {
  return {
    isPending: false,
    error: null as unknown,
    mutateAsync: vi.fn().mockResolvedValue(undefined),
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
  usePinConversationMutation: () => pinMutationState,
  useUnpinConversationMutation: () => idleMutationMock(),
  useHideDmMutation: () => hideMutationState,
  useLeaveGroupMutation: () => idleMutationMock(),
  useDeleteGroupMutation: () => idleMutationMock(),
}))

vi.mock('../components/chat-realtime-provider', () => ({
  useOptionalChatRealtime: () => ({
    connectionStatus: 'reconnecting',
    clearLocalMessagesForConversation: () => undefined,
  }),
}))

vi.mock('./chat-conversation-page', () => ({
  ChatConversationPage: ({
    conversationId,
    embedded,
  }: {
    conversationId: string
    embedded?: boolean
  }) =>
    createElement('div', {
      'data-testid': 'chat-conversation-stub',
      'data-conversation-id': conversationId,
      'data-embedded': embedded ? 'true' : 'false',
    }),
}))

function renderChatPage(props: { selectedConversationId?: string | null } = {}) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })

  return render(
    createElement(
      QueryClientProvider,
      { client: queryClient },
      createElement(ChatPage, {
        onOpenConversation: () => undefined,
        selectedConversationId: props.selectedConversationId ?? null,
      }),
    ),
  )
}

describe('ChatPage flat conversation list', () => {
  beforeEach(() => {
    runtimeState.current = 'web'
    lgViewportState.current = false
    statusQueryMock.mockReturnValue(buildStatusQueryState())
    conversationsQueryMock.mockReturnValue(buildConversationsQueryState())
    pinMutationState.isPending = false
    pinMutationState.error = null
    pinMutationState.mutateAsync.mockReset()
    pinMutationState.mutateAsync.mockResolvedValue(undefined)
    pinMutationState.reset.mockClear()
    hideMutationState.isPending = false
    hideMutationState.error = null
    hideMutationState.mutateAsync.mockReset()
    hideMutationState.mutateAsync.mockResolvedValue(undefined)
    hideMutationState.reset.mockClear()
    vi.stubGlobal('confirm', vi.fn(() => true))
  })

  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
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

  it('renders the desktop split with an empty invite and a single reconnect banner', () => {
    lgViewportState.current = true
    runtimeState.current = 'web'
    conversationsQueryMock.mockReturnValue(
      buildConversationsQueryState({
        data: { items: [buildConversation('conv-dm', 'dm')] },
      }),
    )

    renderChatPage()

    expect(screen.getByTestId('chat-desktop-split')).toBeTruthy()
    expect(screen.getByTestId('chat-desktop-empty')).toBeTruthy()
    expect(screen.getByTestId('chat-desktop-empty-header')).toBeTruthy()
    expect(screen.getByTestId('chat-discussions-rail').getAttribute('data-collapsed')).toBe(
      'false',
    )
    expect(screen.getAllByRole('status')).toHaveLength(1)
  })

  it('collapses the discussions rail to avatars and keeps selection identifiable', () => {
    lgViewportState.current = true
    runtimeState.current = 'web'
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

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })
    const onOpenConversation = () => undefined

    const { rerender } = render(
      createElement(
        QueryClientProvider,
        { client: queryClient },
        createElement(ChatPage, {
          onOpenConversation,
          selectedConversationId: 'conv-group',
        }),
      ),
    )

    fireEvent.click(screen.getByTestId('chat-discussions-collapse'))

    const rail = screen.getByTestId('chat-discussions-rail')
    expect(rail.getAttribute('data-collapsed')).toBe('true')
    expect(screen.queryByTestId('chat-list-search')).toBeNull()
    expect(screen.getByLabelText('Développer les discussions')).toBeTruthy()
    expect(screen.getByLabelText('Nouvelle conversation')).toBeTruthy()

    const groupAvatar = screen.getByTestId('chat-conversation-avatar-conv-group')
    expect(groupAvatar.getAttribute('aria-label')).toBe('Équipe cuisine')
    expect(groupAvatar.getAttribute('aria-current')).toBe('true')
    expect(groupAvatar.getAttribute('title')).toBe('Équipe cuisine')
    expect(screen.getByText('ÉC')).toBeTruthy()
    expect(screen.getByTestId('chat-conversation-avatar-conv-dm').getAttribute('aria-label')).toBe(
      'Bob Martin',
    )
    expect(screen.queryByTestId('chat-conversation-row-conv-dm')).toBeNull()

    rerender(
      createElement(
        QueryClientProvider,
        { client: queryClient },
        createElement(ChatPage, {
          onOpenConversation,
          selectedConversationId: 'conv-dm',
        }),
      ),
    )

    expect(screen.getByTestId('chat-discussions-rail').getAttribute('data-collapsed')).toBe(
      'true',
    )
    expect(screen.getByTestId('chat-conversation-avatar-conv-dm').getAttribute('aria-current')).toBe(
      'true',
    )
  })

  it('resets the collapsed discussions rail when ChatPage remounts', () => {
    lgViewportState.current = true
    runtimeState.current = 'web'
    conversationsQueryMock.mockReturnValue(
      buildConversationsQueryState({
        data: { items: [buildConversation('conv-dm', 'dm')] },
      }),
    )

    const { unmount } = renderChatPage()
    fireEvent.click(screen.getByTestId('chat-discussions-collapse'))
    expect(screen.getByTestId('chat-discussions-rail').getAttribute('data-collapsed')).toBe(
      'true',
    )
    unmount()

    renderChatPage()
    expect(screen.getByTestId('chat-discussions-rail').getAttribute('data-collapsed')).toBe(
      'false',
    )
    expect(screen.getByTestId('chat-list-search')).toBeTruthy()
  })

  it('keeps conversation actions open with a visible error when pin fails', async () => {
    const networkError = new TypeError('Failed to fetch')
    pinMutationState.mutateAsync.mockImplementation(async () => {
      pinMutationState.error = networkError
      throw networkError
    })
    conversationsQueryMock.mockReturnValue(
      buildConversationsQueryState({
        data: { items: [buildConversation('conv-dm', 'dm')] },
      }),
    )

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })
    const tree = () =>
      createElement(
        QueryClientProvider,
        { client: queryClient },
        createElement(ChatPage, {
          onOpenConversation: () => undefined,
          selectedConversationId: null,
        }),
      )
    const { rerender } = render(tree())

    fireEvent.click(screen.getByLabelText('Actions pour Bob Martin'))
    fireEvent.click(screen.getByRole('menuitem', { name: 'Épingler' }))

    await waitFor(() => {
      expect(pinMutationState.mutateAsync).toHaveBeenCalled()
    })
    rerender(tree())

    expect(screen.getByRole('alert')).toBeTruthy()
    expect(screen.getByRole('menuitem', { name: 'Épingler' })).toBeTruthy()
  })

  it('clears a previous actions error when opening another conversation menu', async () => {
    const networkError = new TypeError('Failed to fetch')
    pinMutationState.mutateAsync.mockImplementation(async () => {
      pinMutationState.error = networkError
      throw networkError
    })
    conversationsQueryMock.mockReturnValue(
      buildConversationsQueryState({
        data: {
          items: [
            buildConversation('conv-a', 'dm', { peerDisplayName: 'Alice Peer' }),
            buildConversation('conv-b', 'dm', { peerDisplayName: 'Bob Martin' }),
          ],
        },
      }),
    )

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })
    const tree = () =>
      createElement(
        QueryClientProvider,
        { client: queryClient },
        createElement(ChatPage, {
          onOpenConversation: () => undefined,
          selectedConversationId: null,
        }),
      )
    const { rerender } = render(tree())

    fireEvent.click(screen.getByLabelText('Actions pour Alice Peer'))
    fireEvent.click(screen.getByRole('menuitem', { name: 'Épingler' }))
    await waitFor(() => {
      expect(pinMutationState.mutateAsync).toHaveBeenCalled()
    })
    rerender(tree())
    expect(screen.getByRole('alert')).toBeTruthy()

    fireEvent.click(screen.getByLabelText('Actions pour Bob Martin'))
    expect(pinMutationState.reset).toHaveBeenCalled()
    expect(screen.queryByRole('alert')).toBeNull()
  })

  it('closes conversation actions after a successful pin', async () => {
    conversationsQueryMock.mockReturnValue(
      buildConversationsQueryState({
        data: { items: [buildConversation('conv-dm', 'dm')] },
      }),
    )

    renderChatPage()

    fireEvent.click(screen.getByLabelText('Actions pour Bob Martin'))
    expect(screen.getByRole('menuitem', { name: 'Épingler' })).toBeTruthy()
    fireEvent.click(screen.getByRole('menuitem', { name: 'Épingler' }))

    await waitFor(() => {
      expect(pinMutationState.mutateAsync).toHaveBeenCalledWith('conv-dm')
    })
    await waitFor(() => {
      expect(screen.queryByRole('menuitem', { name: 'Épingler' })).toBeNull()
    })
  })

  it('resets action errors when the desktop popover is dismissed', async () => {
    lgViewportState.current = true
    runtimeState.current = 'web'
    const networkError = new TypeError('Failed to fetch')
    pinMutationState.mutateAsync.mockImplementation(async () => {
      pinMutationState.error = networkError
      throw networkError
    })
    conversationsQueryMock.mockReturnValue(
      buildConversationsQueryState({
        data: { items: [buildConversation('conv-dm', 'dm')] },
      }),
    )

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })
    const tree = () =>
      createElement(
        QueryClientProvider,
        { client: queryClient },
        createElement(ChatPage, {
          onOpenConversation: () => undefined,
          selectedConversationId: null,
        }),
      )
    const { rerender } = render(tree())

    fireEvent.click(screen.getByLabelText('Actions pour Bob Martin'))
    fireEvent.click(screen.getByRole('menuitem', { name: 'Épingler' }))
    await waitFor(() => {
      expect(pinMutationState.mutateAsync).toHaveBeenCalled()
    })
    rerender(tree())
    expect(screen.getByRole('alert')).toBeTruthy()

    fireEvent.click(screen.getByLabelText('Actions pour Bob Martin'))
    await waitFor(() => {
      expect(
        screen.getByLabelText('Actions pour Bob Martin').getAttribute('aria-expanded'),
      ).toBe('false')
    })
    expect(pinMutationState.reset).toHaveBeenCalled()

    fireEvent.click(screen.getByLabelText('Actions pour Bob Martin'))
    expect(screen.queryByRole('alert')).toBeNull()
  })

  it('keeps the desktop actions popover open with a visible error when pin fails', async () => {
    lgViewportState.current = true
    runtimeState.current = 'web'
    const networkError = new TypeError('Failed to fetch')
    pinMutationState.mutateAsync.mockImplementation(async () => {
      pinMutationState.error = networkError
      throw networkError
    })
    conversationsQueryMock.mockReturnValue(
      buildConversationsQueryState({
        data: { items: [buildConversation('conv-dm', 'dm')] },
      }),
    )

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })
    const tree = () =>
      createElement(
        QueryClientProvider,
        { client: queryClient },
        createElement(ChatPage, {
          onOpenConversation: () => undefined,
          selectedConversationId: null,
        }),
      )
    const { rerender } = render(tree())

    fireEvent.click(screen.getByLabelText('Actions pour Bob Martin'))
    expect(screen.getByLabelText('Actions pour Bob Martin').getAttribute('aria-expanded')).toBe(
      'true',
    )
    fireEvent.click(screen.getByRole('menuitem', { name: 'Épingler' }))

    await waitFor(() => {
      expect(pinMutationState.mutateAsync).toHaveBeenCalled()
    })
    rerender(tree())

    expect(screen.getByRole('alert')).toBeTruthy()
    expect(screen.getByRole('menuitem', { name: 'Épingler' })).toBeTruthy()
  })

  it('does not close B or clear B pending when A pin succeeds after B hide started', async () => {
    let resolvePin: (() => void) | undefined
    const pinDeferred = new Promise<void>((resolve) => {
      resolvePin = resolve
    })
    let resolveHide: (() => void) | undefined
    const hideDeferred = new Promise<void>((resolve) => {
      resolveHide = resolve
    })

    pinMutationState.mutateAsync.mockImplementation(async () => {
      pinMutationState.isPending = true
      await pinDeferred
      pinMutationState.isPending = false
    })
    hideMutationState.mutateAsync.mockImplementation(async () => {
      hideMutationState.isPending = true
      await hideDeferred
      hideMutationState.isPending = false
    })
    conversationsQueryMock.mockReturnValue(
      buildConversationsQueryState({
        data: {
          items: [
            buildConversation('conv-a', 'dm', { peerDisplayName: 'Alice Peer' }),
            buildConversation('conv-b', 'dm', { peerDisplayName: 'Bob Martin' }),
          ],
        },
      }),
    )

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })
    const tree = () =>
      createElement(
        QueryClientProvider,
        { client: queryClient },
        createElement(ChatPage, {
          onOpenConversation: () => undefined,
          selectedConversationId: null,
        }),
      )
    const { rerender } = render(tree())

    fireEvent.click(screen.getByLabelText('Actions pour Alice Peer'))
    fireEvent.click(screen.getByRole('menuitem', { name: 'Épingler' }))
    await waitFor(() => {
      expect(pinMutationState.mutateAsync).toHaveBeenCalledWith('conv-a')
    })

    fireEvent.click(screen.getByLabelText('Actions pour Bob Martin'))
    hideMutationState.reset.mockClear()
    pinMutationState.reset.mockClear()
    fireEvent.click(screen.getByRole('menuitem', { name: 'Supprimer la conversation' }))
    await waitFor(() => {
      expect(hideMutationState.mutateAsync).toHaveBeenCalledWith('conv-b')
    })
    hideMutationState.isPending = true
    rerender(tree())

    const hideResetsBeforeSettle = hideMutationState.reset.mock.calls.length
    const pinResetsBeforeSettle = pinMutationState.reset.mock.calls.length
    resolvePin?.()
    await waitFor(() => {
      expect(pinMutationState.isPending).toBe(false)
    })
    rerender(tree())

    expect(screen.getByRole('menuitem', { name: 'Supprimer la conversation' })).toBeTruthy()
    expect(screen.queryByRole('alert')).toBeNull()
    expect(hideMutationState.reset.mock.calls.length).toBe(hideResetsBeforeSettle)
    expect(pinMutationState.reset.mock.calls.length).toBe(pinResetsBeforeSettle)

    resolveHide?.()
  })

  it('does not close B or paint A error when A pin fails after B hide started', async () => {
    let rejectPin: ((error: unknown) => void) | undefined
    const pinDeferred = new Promise<void>((_resolve, reject) => {
      rejectPin = reject
    })
    let resolveHide: (() => void) | undefined
    const hideDeferred = new Promise<void>((resolve) => {
      resolveHide = resolve
    })

    pinMutationState.mutateAsync.mockImplementation(async () => {
      pinMutationState.isPending = true
      try {
        await pinDeferred
      } catch (error) {
        pinMutationState.isPending = false
        pinMutationState.error = error
        throw error
      }
      pinMutationState.isPending = false
    })
    hideMutationState.mutateAsync.mockImplementation(async () => {
      hideMutationState.isPending = true
      await hideDeferred
      hideMutationState.isPending = false
    })
    conversationsQueryMock.mockReturnValue(
      buildConversationsQueryState({
        data: {
          items: [
            buildConversation('conv-a', 'dm', { peerDisplayName: 'Alice Peer' }),
            buildConversation('conv-b', 'dm', { peerDisplayName: 'Bob Martin' }),
          ],
        },
      }),
    )

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })
    const tree = () =>
      createElement(
        QueryClientProvider,
        { client: queryClient },
        createElement(ChatPage, {
          onOpenConversation: () => undefined,
          selectedConversationId: null,
        }),
      )
    const { rerender } = render(tree())

    fireEvent.click(screen.getByLabelText('Actions pour Alice Peer'))
    fireEvent.click(screen.getByRole('menuitem', { name: 'Épingler' }))
    await waitFor(() => {
      expect(pinMutationState.mutateAsync).toHaveBeenCalledWith('conv-a')
    })

    fireEvent.click(screen.getByLabelText('Actions pour Bob Martin'))
    hideMutationState.reset.mockClear()
    pinMutationState.reset.mockClear()
    fireEvent.click(screen.getByRole('menuitem', { name: 'Supprimer la conversation' }))
    await waitFor(() => {
      expect(hideMutationState.mutateAsync).toHaveBeenCalledWith('conv-b')
    })
    hideMutationState.isPending = true
    rerender(tree())

    const hideResetsBeforeSettle = hideMutationState.reset.mock.calls.length
    const pinResetsBeforeSettle = pinMutationState.reset.mock.calls.length
    rejectPin?.(new TypeError('Failed to fetch'))
    await waitFor(() => {
      expect(pinMutationState.error).toBeTruthy()
    })
    rerender(tree())

    expect(screen.getByRole('menuitem', { name: 'Supprimer la conversation' })).toBeTruthy()
    expect(screen.queryByRole('alert')).toBeNull()
    expect(hideMutationState.reset.mock.calls.length).toBe(hideResetsBeforeSettle)
    expect(pinMutationState.reset.mock.calls.length).toBe(pinResetsBeforeSettle)

    resolveHide?.()
  })

  it('keeps B pin pending when a late A pin succeeds on the same mutation (desktop)', async () => {
    lgViewportState.current = true
    runtimeState.current = 'web'

    const pinInFlight = new Set<string>()
    const pinWaiters = new Map<
      string,
      { resolve: () => void; reject: (error: unknown) => void }
    >()

    pinMutationState.mutateAsync.mockImplementation(async (conversationId: string) => {
      pinInFlight.add(conversationId)
      pinMutationState.isPending = true
      pinMutationState.error = null
      try {
        await new Promise<void>((resolve, reject) => {
          pinWaiters.set(conversationId, { resolve, reject })
        })
      } catch (error) {
        pinInFlight.delete(conversationId)
        pinMutationState.isPending = pinInFlight.size > 0
        pinMutationState.error = error
        throw error
      }
      pinInFlight.delete(conversationId)
      pinMutationState.isPending = pinInFlight.size > 0
    })

    conversationsQueryMock.mockReturnValue(
      buildConversationsQueryState({
        data: {
          items: [
            buildConversation('conv-a', 'dm', { peerDisplayName: 'Alice Peer' }),
            buildConversation('conv-b', 'dm', { peerDisplayName: 'Bob Martin' }),
          ],
        },
      }),
    )

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })
    const tree = () =>
      createElement(
        QueryClientProvider,
        { client: queryClient },
        createElement(ChatPage, {
          onOpenConversation: () => undefined,
          selectedConversationId: null,
        }),
      )
    const { rerender } = render(tree())

    fireEvent.click(screen.getByLabelText('Actions pour Alice Peer'))
    fireEvent.click(screen.getByRole('menuitem', { name: 'Épingler' }))
    await waitFor(() => {
      expect(pinMutationState.mutateAsync).toHaveBeenCalledWith('conv-a')
    })

    fireEvent.click(screen.getByLabelText('Actions pour Bob Martin'))
    expect(screen.getByLabelText('Actions pour Bob Martin').getAttribute('aria-expanded')).toBe(
      'true',
    )
    fireEvent.click(screen.getByRole('menuitem', { name: 'Épingler' }))
    await waitFor(() => {
      expect(pinMutationState.mutateAsync).toHaveBeenCalledWith('conv-b')
    })
    pinMutationState.isPending = true
    rerender(tree())

    expect(screen.getByRole('menuitem', { name: 'Épingler' }).hasAttribute('disabled')).toBe(
      true,
    )
    expect(screen.queryByRole('alert')).toBeNull()

    pinWaiters.get('conv-a')?.resolve()
    await waitFor(() => {
      expect(pinInFlight.has('conv-a')).toBe(false)
    })
    pinMutationState.isPending = pinInFlight.size > 0
    rerender(tree())

    expect(screen.getByLabelText('Actions pour Bob Martin').getAttribute('aria-expanded')).toBe(
      'true',
    )
    expect(screen.getByRole('menuitem', { name: 'Épingler' }).hasAttribute('disabled')).toBe(
      true,
    )
    expect(screen.queryByRole('alert')).toBeNull()

    pinWaiters.get('conv-b')?.resolve()
    await waitFor(() => {
      expect(screen.queryByRole('menuitem', { name: 'Épingler' })).toBeNull()
    })
    expect(screen.getByLabelText('Actions pour Bob Martin').getAttribute('aria-expanded')).toBe(
      'false',
    )
  })

  it('keeps B pin pending and hides A error when a late A pin fails on the same mutation (desktop)', async () => {
    lgViewportState.current = true
    runtimeState.current = 'web'

    const pinInFlight = new Set<string>()
    const pinWaiters = new Map<
      string,
      { resolve: () => void; reject: (error: unknown) => void }
    >()

    pinMutationState.mutateAsync.mockImplementation(async (conversationId: string) => {
      pinInFlight.add(conversationId)
      pinMutationState.isPending = true
      pinMutationState.error = null
      try {
        await new Promise<void>((resolve, reject) => {
          pinWaiters.set(conversationId, { resolve, reject })
        })
      } catch (error) {
        pinInFlight.delete(conversationId)
        pinMutationState.isPending = pinInFlight.size > 0
        pinMutationState.error = error
        throw error
      }
      pinInFlight.delete(conversationId)
      pinMutationState.isPending = pinInFlight.size > 0
    })

    conversationsQueryMock.mockReturnValue(
      buildConversationsQueryState({
        data: {
          items: [
            buildConversation('conv-a', 'dm', { peerDisplayName: 'Alice Peer' }),
            buildConversation('conv-b', 'dm', { peerDisplayName: 'Bob Martin' }),
          ],
        },
      }),
    )

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })
    const tree = () =>
      createElement(
        QueryClientProvider,
        { client: queryClient },
        createElement(ChatPage, {
          onOpenConversation: () => undefined,
          selectedConversationId: null,
        }),
      )
    const { rerender } = render(tree())

    fireEvent.click(screen.getByLabelText('Actions pour Alice Peer'))
    fireEvent.click(screen.getByRole('menuitem', { name: 'Épingler' }))
    await waitFor(() => {
      expect(pinMutationState.mutateAsync).toHaveBeenCalledWith('conv-a')
    })

    fireEvent.click(screen.getByLabelText('Actions pour Bob Martin'))
    fireEvent.click(screen.getByRole('menuitem', { name: 'Épingler' }))
    await waitFor(() => {
      expect(pinMutationState.mutateAsync).toHaveBeenCalledWith('conv-b')
    })
    pinMutationState.isPending = true
    rerender(tree())

    pinWaiters.get('conv-a')?.reject(new Error('pin-a-failed'))
    await waitFor(() => {
      expect(pinInFlight.has('conv-a')).toBe(false)
    })
    pinMutationState.isPending = pinInFlight.size > 0
    rerender(tree())

    expect(screen.getByLabelText('Actions pour Bob Martin').getAttribute('aria-expanded')).toBe(
      'true',
    )
    expect(screen.getByRole('menuitem', { name: 'Épingler' }).hasAttribute('disabled')).toBe(
      true,
    )
    expect(screen.queryByRole('alert')).toBeNull()
    expect(screen.queryByText('pin-a-failed')).toBeNull()

    pinWaiters.get('conv-b')?.reject(new Error('pin-b-failed'))
    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeTruthy()
    })
    rerender(tree())

    expect(screen.getByText('pin-b-failed')).toBeTruthy()
    expect(screen.queryByText('pin-a-failed')).toBeNull()
    expect(screen.getByLabelText('Actions pour Bob Martin').getAttribute('aria-expanded')).toBe(
      'true',
    )
    expect(screen.getByRole('menuitem', { name: 'Épingler' })).toBeTruthy()
  })

  it('embeds the selected conversation on desktop web', () => {
    lgViewportState.current = true
    runtimeState.current = 'web'
    conversationsQueryMock.mockReturnValue(
      buildConversationsQueryState({
        data: { items: [buildConversation('conv-dm', 'dm')] },
      }),
    )

    renderChatPage({ selectedConversationId: 'conv-dm' })

    const stub = screen.getByTestId('chat-conversation-stub')
    expect(stub.getAttribute('data-conversation-id')).toBe('conv-dm')
    expect(stub.getAttribute('data-embedded')).toBe('true')
    expect(screen.queryByTestId('chat-desktop-empty')).toBeNull()
  })

  it('keeps the stacked list on native large viewports', () => {
    lgViewportState.current = true
    runtimeState.current = 'native'
    conversationsQueryMock.mockReturnValue(
      buildConversationsQueryState({
        data: { items: [buildConversation('conv-dm', 'dm')] },
      }),
    )

    renderChatPage({ selectedConversationId: 'conv-dm' })

    expect(screen.queryByTestId('chat-desktop-split')).toBeNull()
    expect(screen.queryByTestId('chat-conversation-stub')).toBeNull()
  })

})

describe('ChatPage scroll layout', () => {
  beforeEach(() => {
    runtimeState.current = 'web'
    lgViewportState.current = false
    statusQueryMock.mockReturnValue(buildStatusQueryState())
    conversationsQueryMock.mockReturnValue(buildConversationsQueryState())
  })

  afterEach(() => {
    cleanup()
  })

  function expectChatPageRoot() {
    return screen.getByTestId('chat-page-root')
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
