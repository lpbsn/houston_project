// @vitest-environment jsdom

import { createElement } from 'react'
import { QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { AppRoute } from '@/app/app-routes'
import type { BootstrapResponse, Membership } from '@/features/auth/types'
import { queryClient } from '@/lib/query-client'

const navigate = vi.fn()
const routeState = vi.hoisted(() => ({
  route: { kind: 'static', path: '/chat' } as AppRoute,
}))
const authState = vi.hoisted(() => ({
  isReady: true,
  isAuthenticated: true,
  isLoggingIn: false,
  isLoggingOut: false,
  login: vi.fn(),
  logout: vi.fn(),
  loginError: null,
  bootstrap: null as BootstrapResponse | null,
  hasOperationalAccess: true,
  pendingOnboardingMemberships: [] as unknown[],
  memberships: [] as Membership[],
}))
const runtimeState = vi.hoisted(() => ({ current: 'web' as 'web' | 'native' }))

vi.mock('@/lib/runtime', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/runtime')>()
  return {
    ...actual,
    getAppRuntime: () => runtimeState.current,
  }
})

vi.mock('@/app/app-routes', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/app/app-routes')>()
  return {
    ...actual,
    useAppRoute: () => ({
      route: routeState.route,
      navigate,
      search: window.location.search,
    }),
  }
})

vi.mock('@/app/auth-provider', () => ({
  useAuth: () => authState,
}))

vi.mock('@/features/chat/lib/chat-outbox', () => ({
  composerDraftId: (userId: string, establishmentId: string, conversationId: string) =>
    `${userId}:${establishmentId}:${conversationId}`,
  loadComposerDraft: vi.fn(async () => null),
  saveComposerDraft: vi.fn(async () => undefined),
  persistChatOutboxAttachmentBytes: vi.fn(async () => 'relative/path'),
  readChatOutboxAttachmentBytes: vi.fn(async () => null),
  clearChatOutbox: vi.fn(async () => undefined),
  clearExpiredChatOutboxAttachments: vi.fn(async () => undefined),
  loadChatOutboxDrafts: vi.fn(async () => []),
  saveChatOutboxDraft: vi.fn(async () => undefined),
}))

const chatFixtures = vi.hoisted(() => {
  function listItem(
    id: string,
    peerDisplayName: string,
  ): {
    id: string
    type: 'dm'
    title: string
    created_at: string
    unread: boolean
    unread_count: number
    last_message_at: string
    last_message_preview: { body: string; created_at: string }
    participants: Array<{
      membership_id: string
      user_id: string
      display_name: string
      role: 'staff' | 'manager'
      participant_role: 'member'
    }>
    pinned: boolean
    can_delete: boolean
  } {
    return {
      id,
      type: 'dm',
      title: '',
      created_at: '2026-06-13T11:00:00Z',
      unread: false,
      unread_count: 0,
      last_message_at: '2026-06-13T12:00:00Z',
      last_message_preview: {
        body: `Preview ${peerDisplayName}`,
        created_at: '2026-06-13T12:00:00Z',
      },
      participants: [
        {
          membership_id: 'mbr-viewer',
          user_id: 'user-viewer',
          display_name: 'Alice',
          role: 'staff',
          participant_role: 'member',
        },
        {
          membership_id: `mbr-${id}`,
          user_id: `user-${id}`,
          display_name: peerDisplayName,
          role: 'manager',
          participant_role: 'member',
        },
      ],
      pinned: false,
      can_delete: false,
    }
  }

  return {
    byEstablishment: {
      'est-1': [listItem('conv-a', 'Alpha Peer'), listItem('conv-b', 'Beta Peer')],
      'est-2': [listItem('conv-z', 'Zulu Peer')],
    } as Record<string, ReturnType<typeof listItem>[]>,
    detail: (conversationId: string) => {
      const peer =
        conversationId === 'conv-a'
          ? 'Alpha Peer'
          : conversationId === 'conv-b'
            ? 'Beta Peer'
            : 'Zulu Peer'
      const base = listItem(conversationId, peer)
      return {
        id: base.id,
        type: base.type,
        title: base.title,
        created_at: base.created_at,
        last_message_at: base.last_message_at,
        unread: base.unread,
        participants: base.participants,
        can_manage: false,
        can_delete: false,
        pinned: false,
      }
    },
    message: (conversationId: string) => ({
      id: `msg-${conversationId}`,
      author_membership_id: 'mbr-viewer',
      author_display_name: 'Alice',
      body: `Hello ${conversationId}`,
      client_message_id: `client-${conversationId}`,
      created_at: '2026-06-13T12:00:00Z',
      is_reply: false,
      reply_to: null,
      mentions: [],
      attachments: [],
    }),
  }
})

vi.mock('@/features/chat/hooks', () => ({
  useChatAvailability: () => ({
    isNavVisible: true,
    statusResolved: true,
    isRuntimeAvailable: true,
  }),
  useChatConversationsQuery: (establishmentId: string | null) => ({
    isLoading: false,
    isError: false,
    isSuccess: true,
    data: {
      items: establishmentId ? (chatFixtures.byEstablishment[establishmentId] ?? []) : [],
    },
  }),
  useChatStatusQuery: () => ({
    isLoading: false,
    isError: false,
    data: {
      can_access: true,
      chat_enabled: true,
      can_create_dm: true,
      can_create_group: true,
      can_manage_settings: false,
    },
  }),
  useChatConversationDetailQuery: (_establishmentId: string | null, conversationId: string) => ({
    isLoading: false,
    isError: false,
    isSuccess: true,
    data: chatFixtures.detail(conversationId),
    refetch: vi.fn(),
  }),
  useChatMessagesInfiniteQuery: (_establishmentId: string | null, conversationId: string) => ({
    isLoading: false,
    isError: false,
    isSuccess: true,
    hasNextPage: false,
    isFetchingNextPage: false,
    fetchNextPage: vi.fn(),
    data: {
      pages: [{ items: [chatFixtures.message(conversationId)], has_more: false }],
      pageParams: [undefined],
    },
    refetch: vi.fn(),
  }),
  useMarkConversationSeenMutation: () => ({ mutate: vi.fn() }),
  useEligibleChatMembershipsQuery: () => ({
    isLoading: false,
    isError: false,
    data: { items: [] },
  }),
  useCreateDmMutation: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
    reset: vi.fn(),
    error: null,
  }),
  useCreateGroupMutation: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
    reset: vi.fn(),
    error: null,
  }),
  usePinConversationMutation: () => ({
    isPending: false,
    mutateAsync: vi.fn(),
    reset: vi.fn(),
  }),
  useUnpinConversationMutation: () => ({
    isPending: false,
    mutateAsync: vi.fn(),
    reset: vi.fn(),
  }),
  useHideDmMutation: () => ({
    isPending: false,
    mutateAsync: vi.fn(),
    reset: vi.fn(),
  }),
  useLeaveGroupMutation: () => ({
    isPending: false,
    mutateAsync: vi.fn(),
    reset: vi.fn(),
  }),
  useDeleteGroupMutation: () => ({
    isPending: false,
    mutateAsync: vi.fn(),
    reset: vi.fn(),
  }),
}))

vi.mock('@/features/chat/hooks/use-chat-conversation-presence', () => ({
  useChatConversationPresence: vi.fn(),
}))

vi.mock('@/features/chat/components/chat-realtime-provider', () => ({
  useOptionalChatRealtime: () => ({
    connectionStatus: 'connected',
    localMessages: [],
    sendChatMessage: () => ({ clientMessageId: 'local', queued: false }),
    retryFailedMessage: () => false,
    cancelSendingMessage: () => false,
    clearLocalMessagesForConversation: () => undefined,
  }),
  ChatRealtimeProvider: ({ children }: { children: React.ReactNode }) => children,
}))

vi.mock('@/app/lazy-terrain-pages', async () => {
  const { ChatPage } = await import('@/features/chat/pages/chat-page')
  const { ChatConversationPage } = await import('@/features/chat/pages/chat-conversation-page')
  const Page = ({ name }: { name: string }) => createElement('div', null, name)
  return {
    LazyActionPlanCreatePage: () => createElement(Page, { name: 'action-plan-create' }),
    LazyActionPlanExecutionDetailPage: () => createElement(Page, { name: 'execution-detail' }),
    LazyActionPlanExecutionEditPage: () => createElement(Page, { name: 'execution-edit' }),
    LazyActionPlanHubPage: () => createElement(Page, { name: 'action-plan-hub' }),
    LazyActionPlanTemplateDetailPage: () => createElement(Page, { name: 'template-detail' }),
    LazyAnalyticsPage: () => createElement(Page, { name: 'analytics' }),
    LazyAnalyticsPatternDetailPage: () => createElement(Page, { name: 'analytics-pattern-detail' }),
    LazyChatConversationPage: ChatConversationPage,
    LazyChatPage: ChatPage,
    LazyChatRealtimeProvider: ({ children }: { children: React.ReactNode }) => children,
    LazyComingSoonPage: ({ title }: { title: string }) => createElement('h1', null, title),
    LazyExecutionFeedPage: () => createElement(Page, { name: 'execution' }),
    LazyExecutionUpcomingPage: () => createElement(Page, { name: 'execution-upcoming' }),
    LazyNotificationsCenterPage: () => createElement(Page, { name: 'notifications' }),
    LazyProfilePage: () => createElement(Page, { name: 'profile' }),
    LazyReportPage: () => createElement(Page, { name: 'reporting' }),
    LazySignalDetailPage: () => createElement(Page, { name: 'signal-detail' }),
    LazySignalFeedPage: () => createElement(Page, { name: 'signals' }),
    LazyTeamMemberDetailPage: () => createElement(Page, { name: 'team-member' }),
    LazyTeamPage: () => createElement(Page, { name: 'team' }),
  }
})

vi.mock('@/features/establishment-config/pages/operational-config-page', () => ({
  OperationalConfigPage: () =>
    createElement('div', { 'data-testid': 'operational-config' }, 'operational-config'),
}))

vi.mock('@/features/notifications/components/notification-center', () => ({
  NotificationCenter: () => null,
}))

vi.mock('@/components/layout/network-status-banner', () => ({
  NetworkStatusBanner: () => null,
}))

vi.mock('@/features/realtime/components/operational-reconnect-banner', () => ({
  OperationalReconnectBanner: () => null,
}))

vi.mock('@/features/realtime/components/operational-realtime-provider', () => ({
  OperationalRealtimeProvider: ({ children }: { children: React.ReactNode }) => children,
  useOptionalOperationalRealtime: () => null,
}))

vi.mock('@/features/chat/api', () => ({
  ChatApiError: class ChatApiError extends Error {},
  chatQueryKeys: {
    status: (establishmentId: string) => ['chat', 'status', establishmentId],
    sharedMedia: (...parts: unknown[]) => ['chat', 'shared-media', ...parts],
  },
  fetchChatSharedMedia: vi.fn(async () => ({ items: [], has_more: false })),
}))

vi.mock('@/features/chat/lib/apply-chat-availability-cache', () => ({
  purgeEstablishmentChatOperationalQueries: vi.fn(),
}))

vi.mock('framer-motion', () => ({
  AnimatePresence: ({ children }: { children: React.ReactNode }) => children,
  motion: {
    main: ({ children, ...props }: React.ComponentProps<'main'>) =>
      createElement('main', props, children),
    div: ({ children, className }: { children: React.ReactNode; className?: string }) =>
      createElement('div', { className }, children),
  },
  useReducedMotion: () => true,
}))

import App from './App'

function membership(id: string, establishmentId: string): Membership {
  return {
    id,
    establishment_id: establishmentId,
    establishment_name: `Spore ${establishmentId}`,
    organization_id: 'org-1',
    organization_name: 'Spore',
    role: 'director',
    status: 'active',
    chat_available: true,
    scopes: [],
    scope_summary: { business_unit_count: 0 },
  }
}

function bootstrapActive(establishmentId = 'est-1'): BootstrapResponse {
  const memberships = [
    membership('mbr-viewer', 'est-1'),
    membership('mbr-est-2', 'est-2'),
  ]
  const active =
    memberships.find((item) => item.establishment_id === establishmentId) ?? memberships[0]
  return {
    authenticated: true,
    user: {
      id: 'user-viewer',
      username: 'alice',
      email: 'alice@example.com',
      identity_type: 'human',
      first_name: 'Alice',
      last_name: 'Viewer',
      pending_email: null,
      pending_email_expires_at: null,
      terms_version: 'cgu-v1',
      terms_accepted_at: '2026-01-01T00:00:00.000Z',
      current_terms_version: 'cgu-v1',
      needs_terms_acceptance: false,
      ai_consent_version: 'openai-v1',
      ai_processing_consented_at: '2026-01-01T00:00:00.000Z',
      current_ai_consent_version: 'openai-v1',
      needs_ai_consent: false,
      ai_consent_status: 'granted',
    },
    memberships,
    active_membership: active,
    pending_onboarding_memberships: [],
    permission_hints: {
      chat_available: true,
      can_create_action_plan: false,
      can_create_catalog_action_plan: false,
      can_view_action_plan_catalog: false,
      can_invite: false,
      can_manage_runtime_config: false,
      can_view_team: false,
      can_manage_organization: false,
      platform_operator_active: false,
    },
  }
}

function stubLgViewport(matches: boolean) {
  Object.defineProperty(window, 'matchMedia', {
    configurable: true,
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: query.includes('1024') ? matches : false,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  })
}

function wrapApp() {
  return createElement(QueryClientProvider, { client: queryClient }, createElement(App))
}

describe('App chat desktop navigation', () => {
  beforeEach(() => {
    runtimeState.current = 'web'
    stubLgViewport(true)
    const bootstrap = bootstrapActive()
    authState.bootstrap = bootstrap
    authState.memberships = bootstrap.memberships
    authState.hasOperationalAccess = true
    routeState.route = { kind: 'static', path: '/chat' }
    Element.prototype.scrollTo = vi.fn()
  })

  afterEach(() => {
    cleanup()
    navigate.mockReset()
    routeState.route = { kind: 'static', path: '/chat' }
    authState.bootstrap = null
    authState.hasOperationalAccess = false
    authState.memberships = []
    queryClient.clear()
    Reflect.deleteProperty(window, 'matchMedia')
    runtimeState.current = 'web'
  })

  it('keeps list search and scroll across /chat → /chat/:idA → /chat/:idB while resetting composer draft', async () => {
    const view = render(wrapApp())

    expect(await screen.findByTestId('chat-desktop-split')).toBeTruthy()
    expect(screen.getByTestId('chat-desktop-empty')).toBeTruthy()

    const search = screen.getByTestId('chat-list-search') as HTMLInputElement
    fireEvent.change(search, { target: { value: 'Alpha' } })
    expect(search.value).toBe('Alpha')

    const listScroll = screen.getByTestId('chat-list-scroll')
    Object.defineProperty(listScroll, 'scrollTop', {
      configurable: true,
      writable: true,
      value: 96,
    })
    expect(listScroll.scrollTop).toBe(96)

    const pageRoot = screen.getByTestId('chat-page-root')

    routeState.route = { kind: 'chat-conversation-detail', conversationId: 'conv-a' }
    view.rerender(wrapApp())

    await waitFor(() => {
      expect(
        screen.getByTestId('chat-conversation-page').getAttribute('data-conversation-id'),
      ).toBe('conv-a')
    })
    expect(screen.getByTestId('chat-page-root')).toBe(pageRoot)
    expect((screen.getByTestId('chat-list-search') as HTMLInputElement).value).toBe('Alpha')
    expect(screen.getByTestId('chat-list-scroll').scrollTop).toBe(96)

    const composer = within(screen.getByTestId('chat-conversation-page')).getByPlaceholderText(
      'Écrire un message…',
    ) as HTMLTextAreaElement
    fireEvent.change(composer, { target: { value: 'Brouillon conversation A' } })
    expect(composer.value).toBe('Brouillon conversation A')

    const fileInput = screen
      .getByTestId('chat-conversation-page')
      .querySelector('input[type="file"]') as HTMLInputElement
    expect(fileInput).toBeTruthy()
    const file = new File(['alpha'], 'photo-a.png', { type: 'image/png' })
    fireEvent.change(fileInput, { target: { files: [file] } })
    expect(await screen.findByText('photo-a.png')).toBeTruthy()

    routeState.route = { kind: 'chat-conversation-detail', conversationId: 'conv-b' }
    view.rerender(wrapApp())

    await waitFor(() => {
      expect(
        screen.getByTestId('chat-conversation-page').getAttribute('data-conversation-id'),
      ).toBe('conv-b')
    })

    expect(screen.getByTestId('chat-page-root')).toBe(pageRoot)
    expect((screen.getByTestId('chat-list-search') as HTMLInputElement).value).toBe('Alpha')
    expect(screen.getByTestId('chat-list-scroll').scrollTop).toBe(96)

    const composerB = within(screen.getByTestId('chat-conversation-page')).getByPlaceholderText(
      'Écrire un message…',
    ) as HTMLTextAreaElement
    expect(composerB.value).toBe('')
    expect(screen.queryByText('Brouillon conversation A')).toBeNull()
    expect(screen.queryByText('photo-a.png')).toBeNull()
    expect(screen.getByText('Hello conv-b')).toBeTruthy()
  })

  it('does not use the desktop split on native large viewports', async () => {
    runtimeState.current = 'native'
    stubLgViewport(true)
    routeState.route = { kind: 'static', path: '/chat' }
    render(wrapApp())

    expect(await screen.findByTestId('chat-page-root')).toBeTruthy()
    expect(screen.queryByTestId('chat-desktop-split')).toBeNull()
    expect(screen.queryByTestId('chat-desktop-empty')).toBeNull()
  })

  it('resets list local state when switching establishment from /chat/:id', async () => {
    routeState.route = { kind: 'chat-conversation-detail', conversationId: 'conv-a' }
    const view = render(wrapApp())

    await waitFor(() => {
      expect(
        screen.getByTestId('chat-conversation-page').getAttribute('data-conversation-id'),
      ).toBe('conv-a')
    })

    const search = screen.getByTestId('chat-list-search') as HTMLInputElement
    fireEvent.change(search, { target: { value: 'Alpha' } })
    expect(search.value).toBe('Alpha')
    expect(screen.getByTestId('chat-conversation-row-conv-a')).toBeTruthy()
    expect(screen.getByText('Hello conv-a')).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: 'Nouvelle conversation' }))
    expect(await screen.findByTestId('chat-create-dialog')).toBeTruthy()

    const pageRootA = screen.getByTestId('chat-page-root')

    const bootstrapB = bootstrapActive('est-2')
    authState.bootstrap = bootstrapB
    authState.memberships = bootstrapB.memberships
    routeState.route = {
      kind: 'scoped-terrain',
      scope: { type: 'establishment', establishmentId: 'est-2' },
      page: 'chat',
    }
    view.rerender(wrapApp())

    await waitFor(() => {
      expect(screen.getByTestId('chat-page-root')).not.toBe(pageRootA)
    })

    expect(screen.getByTestId('chat-desktop-empty')).toBeTruthy()
    expect(screen.queryByTestId('chat-conversation-page')).toBeNull()
    expect(screen.queryByTestId('chat-create-dialog')).toBeNull()
    expect((screen.getByTestId('chat-list-search') as HTMLInputElement).value).toBe('')
    expect(screen.queryByTestId('chat-conversation-row-conv-a')).toBeNull()
    expect(screen.queryByText('Hello conv-a')).toBeNull()
    expect(screen.getByTestId('chat-conversation-row-conv-z')).toBeTruthy()
  })
})
