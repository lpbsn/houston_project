// @vitest-environment jsdom

import { createElement } from 'react'
import { QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { AppRoute } from '@/app/app-routes'
import type { BootstrapResponse, Membership } from '@/features/auth/types'
import { buildSelectEstablishmentRedirectHref } from '@/lib/app-open-target'
import { queryClient } from '@/lib/query-client'

const navigate = vi.fn()
const switchEstablishment = vi.hoisted(() => vi.fn())
const routeState = vi.hoisted(() => ({
  route: { kind: 'static', path: '/analytics' } as AppRoute,
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
  hasOperationalAccess: false,
  pendingOnboardingMemberships: [] as unknown[],
  memberships: [] as Membership[],
}))

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

vi.mock('@/app/lazy-terrain-pages', () => {
  const Page = ({ name }: { name: string }) => createElement('div', null, name)
  return {
    LazyActionPlanCreatePage: () => createElement(Page, { name: 'action-plan-create' }),
    LazyActionPlanExecutionDetailPage: () => createElement(Page, { name: 'execution-detail' }),
    LazyActionPlanExecutionEditPage: () => createElement(Page, { name: 'execution-edit' }),
    LazyActionPlanHubPage: () => createElement(Page, { name: 'action-plan-hub' }),
    LazyActionPlanTemplateDetailPage: () => createElement(Page, { name: 'template-detail' }),
    LazyAnalyticsPage: () => createElement(Page, { name: 'analytics' }),
    LazyAnalyticsPatternDetailPage: () => createElement(Page, { name: 'analytics-pattern-detail' }),
    LazyChatConversationPage: () => createElement(Page, { name: 'chat-conversation' }),
    LazyChatPage: () => createElement(Page, { name: 'chat' }),
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

vi.mock('@/features/chat/hooks', () => ({
  useChatAvailability: () => ({
    isNavVisible: false,
    statusResolved: true,
    isRuntimeAvailable: false,
  }),
  useChatConversationsQuery: () => ({ data: { items: [] } }),
}))

vi.mock('@/features/chat/api', () => ({
  chatQueryKeys: {
    status: (establishmentId: string) => ['chat', 'status', establishmentId],
  },
}))

vi.mock('@/features/chat/lib/apply-chat-availability-cache', () => ({
  purgeEstablishmentChatOperationalQueries: vi.fn(),
}))

vi.mock('@/features/auth/pages/select-establishment-page', () => ({
  SelectEstablishmentPage: () =>
    createElement('div', { 'data-testid': 'select-establishment-page' }, 'select-establishment'),
}))

vi.mock('@/features/auth/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/features/auth/api')>()
  return {
    ...actual,
    switchEstablishment: (...args: unknown[]) => switchEstablishment(...args),
  }
})

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
import { bootstrapQueryKey } from '@/features/auth/api'

function membership(
  id: string,
  establishmentId: string,
  role: Membership['role'] = 'director',
): Membership {
  return {
    id,
    establishment_id: establishmentId,
    establishment_name: `Spore ${establishmentId}`,
    organization_id: 'org-1',
    organization_name: 'Spore',
    role,
    status: 'active',
    chat_available: true,
    scopes: [],
    scope_summary: { business_unit_count: 0 },
  }
}

function bootstrapWithoutActiveMembership(
  overrides: Partial<BootstrapResponse> = {},
): BootstrapResponse {
  const memberships = [membership('membership-1', 'est-1'), membership('membership-2', 'est-2')]
  return {
    authenticated: true,
    user: {
      id: 'user-1',
      username: 'marie',
      email: 'marie@example.com',
      identity_type: 'human',
      first_name: 'Marie',
      last_name: 'Renaud',
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
    active_membership: null,
    pending_onboarding_memberships: [],
    permission_hints: {
      chat_available: false,
      can_create_action_plan: false,
      can_create_catalog_action_plan: false,
      can_view_action_plan_catalog: false,
      can_invite: false,
      can_manage_runtime_config: false,
      can_view_team: false,
      can_manage_organization: false,
      platform_operator_active: false,
    },
    ...overrides,
  }
}

function bootstrapWithActiveMembership(): BootstrapResponse {
  const active = membership('membership-1', 'est-1')
  return {
    ...bootstrapWithoutActiveMembership({
      memberships: [active],
      active_membership: active,
    }),
  }
}

function bootstrapWithSelectedEstablishment(establishmentId: string): BootstrapResponse {
  const memberships = [membership('membership-1', 'est-1'), membership('membership-2', 'est-2')]
  const active =
    memberships.find((item) => item.establishment_id === establishmentId) ?? memberships[0]
  return bootstrapWithoutActiveMembership({
    memberships,
    active_membership: active,
  })
}

function stubLgViewport(matches: boolean) {
  Object.defineProperty(window, 'matchMedia', {
    configurable: true,
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches,
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

afterEach(() => {
  try {
    cleanup()
  } finally {
    navigate.mockReset()
    routeState.route = { kind: 'static', path: '/analytics' }
    authState.bootstrap = null
    authState.hasOperationalAccess = false
    authState.memberships = []
    authState.pendingOnboardingMemberships = []
    switchEstablishment.mockReset()
    switchEstablishment.mockResolvedValue(undefined)
    queryClient.clear()
    window.history.replaceState(null, '', '/')
    Reflect.deleteProperty(window, 'matchMedia')
    vi.unstubAllEnvs()
  }
})

describe('App terrain active membership routing', () => {
  it('keeps analytics available without active membership and redirects reporting to selection', async () => {
    const bootstrap = bootstrapWithoutActiveMembership()
    authState.bootstrap = bootstrap
    authState.memberships = bootstrap.memberships
    authState.hasOperationalAccess = false

    const rendered = render(wrapApp())

    expect(navigate).not.toHaveBeenCalled()

    routeState.route = { kind: 'static', path: '/reporting' }
    rendered.rerender(wrapApp())

    await waitFor(() => {
      expect(navigate).toHaveBeenCalledWith('/select-establishment', { replace: true })
    })
  })

  it('keeps reporting after a switch when the Query cache is ahead of AuthProvider', async () => {
    stubLgViewport(false)
    const staleBootstrap = bootstrapWithoutActiveMembership()
    const switchedBootstrap = bootstrapWithSelectedEstablishment('est-2')
    authState.bootstrap = staleBootstrap
    authState.memberships = staleBootstrap.memberships
    authState.hasOperationalAccess = false
    queryClient.setQueryData(bootstrapQueryKey, switchedBootstrap)
    routeState.route = { kind: 'static', path: '/reporting' }

    render(wrapApp())

    expect(navigate).not.toHaveBeenCalled()
    expect(await screen.findByText('reporting')).toBeTruthy()
  })

  it('does not bounce a scoped destination when the cache already matches the route establishment', async () => {
    stubLgViewport(false)
    const staleBootstrap = bootstrapWithSelectedEstablishment('est-1')
    const switchedBootstrap = bootstrapWithSelectedEstablishment('est-2')
    authState.bootstrap = staleBootstrap
    authState.memberships = staleBootstrap.memberships
    authState.hasOperationalAccess = true
    queryClient.setQueryData(bootstrapQueryKey, switchedBootstrap)
    routeState.route = {
      kind: 'scoped-terrain',
      scope: { type: 'establishment', establishmentId: 'est-2' },
      page: 'chat',
    }

    render(wrapApp())

    expect(navigate).not.toHaveBeenCalledWith(
      expect.stringMatching(/^\/select-establishment/),
      expect.anything(),
    )
    expect(switchEstablishment).not.toHaveBeenCalled()
  })

  it('keeps the cross dashboard without a selected establishment', () => {
    const bootstrap = bootstrapWithoutActiveMembership()
    authState.bootstrap = bootstrap
    authState.memberships = bootstrap.memberships
    authState.hasOperationalAccess = false
    routeState.route = {
      kind: 'scoped-terrain',
      scope: { type: 'cross' },
      page: 'dashboard',
    }

    render(wrapApp())

    expect(screen.getByRole('heading', { name: 'Dashboard Cross' })).toBeTruthy()
    expect(navigate).not.toHaveBeenCalled()
  })

  it('does not redirect /analytics to Cross when no establishment is selected', async () => {
    stubLgViewport(true)
    const bootstrap = bootstrapWithoutActiveMembership()
    authState.bootstrap = bootstrap
    authState.memberships = bootstrap.memberships
    authState.hasOperationalAccess = false

    render(wrapApp())

    expect(navigate).not.toHaveBeenCalled()
    expect(screen.getByText('analytics')).toBeTruthy()
  })

  it('redirects /analytics to the selected establishment dashboard', async () => {
    stubLgViewport(true)
    const bootstrap = bootstrapWithActiveMembership()
    authState.bootstrap = bootstrap
    authState.memberships = bootstrap.memberships
    authState.hasOperationalAccess = true

    render(wrapApp())

    await waitFor(() => {
      expect(navigate).toHaveBeenCalledWith('/e/est-1?period=7d', { replace: true })
    })
  })

  it('switches to a pending establishment before opening the target from login', async () => {
    stubLgViewport(true)
    window.history.replaceState(
      null,
      '',
      '/login?next=%2Fsignals%2F11111111-1111-4111-8111-111111111111&establishment_id=est-1',
    )
    const bootstrap = bootstrapWithoutActiveMembership()
    authState.bootstrap = bootstrap
    authState.memberships = bootstrap.memberships
    authState.hasOperationalAccess = false
    routeState.route = { kind: 'static', path: '/login' }

    render(wrapApp())

    await waitFor(() => {
      expect(switchEstablishment).toHaveBeenCalledWith({ establishment_id: 'est-1' })
    })
    await waitFor(() => {
      expect(navigate).toHaveBeenCalledWith(
        '/signals/11111111-1111-4111-8111-111111111111',
        { replace: true },
      )
    })
    expect(navigate).not.toHaveBeenCalledWith('/cross/signals', { replace: true })
  })

  it('lands a membership-required login next without a hint on the desktop landing', async () => {
    stubLgViewport(true)
    window.history.replaceState(
      null,
      '',
      '/login?next=%2Fsignals%2F11111111-1111-4111-8111-111111111111',
    )
    const bootstrap = bootstrapWithoutActiveMembership()
    authState.bootstrap = bootstrap
    authState.memberships = bootstrap.memberships
    authState.hasOperationalAccess = false
    routeState.route = { kind: 'static', path: '/login' }

    render(wrapApp())

    await waitFor(() => {
      expect(navigate).toHaveBeenCalledWith('/cross/signals', { replace: true })
    })
    expect(switchEstablishment).not.toHaveBeenCalled()
    expect(navigate).not.toHaveBeenCalledWith(
      expect.stringMatching(/^\/select-establishment/),
      expect.anything(),
    )
  })

  it('opens a cross login next without a hint instead of the selector', async () => {
    stubLgViewport(true)
    window.history.replaceState(null, '', '/login?next=%2Fcross%3Fperiod%3D7d')
    const bootstrap = bootstrapWithoutActiveMembership()
    authState.bootstrap = bootstrap
    authState.memberships = bootstrap.memberships
    authState.hasOperationalAccess = false
    routeState.route = { kind: 'static', path: '/login' }

    render(wrapApp())

    await waitFor(() => {
      expect(navigate).toHaveBeenCalledWith('/cross?period=7d', { replace: true })
    })
    expect(switchEstablishment).not.toHaveBeenCalled()
    expect(navigate).not.toHaveBeenCalledWith(
      expect.stringMatching(/^\/select-establishment/),
      expect.anything(),
    )
  })

  it('switches from a login next that encodes an establishment without a query hint', async () => {
    stubLgViewport(true)
    const establishmentId = '11111111-1111-4111-8111-111111111111'
    window.history.replaceState(
      null,
      '',
      `/login?next=${encodeURIComponent(`/e/${establishmentId}/signals`)}`,
    )
    const bootstrap = bootstrapWithoutActiveMembership()
    authState.bootstrap = bootstrap
    authState.memberships = bootstrap.memberships
    authState.hasOperationalAccess = false
    routeState.route = { kind: 'static', path: '/login' }

    render(wrapApp())

    await waitFor(() => {
      expect(switchEstablishment).toHaveBeenCalledWith({ establishment_id: establishmentId })
    })
    await waitFor(() => {
      expect(navigate).toHaveBeenCalledWith(`/e/${establishmentId}/signals`, { replace: true })
    })
    expect(navigate).not.toHaveBeenCalledWith('/cross/signals', { replace: true })
    expect(navigate).not.toHaveBeenCalledWith(
      expect.stringMatching(/^\/select-establishment/),
      expect.anything(),
    )
  })

  it('carries a membership-required login next without a hint to the selector on a small viewport', async () => {
    window.history.replaceState(
      null,
      '',
      '/login?next=%2Fsignals%2F11111111-1111-4111-8111-111111111111',
    )
    const bootstrap = bootstrapWithoutActiveMembership()
    authState.bootstrap = bootstrap
    authState.memberships = bootstrap.memberships
    authState.hasOperationalAccess = false
    routeState.route = { kind: 'static', path: '/login' }

    render(wrapApp())

    await waitFor(() => {
      expect(navigate).toHaveBeenCalledWith(
        buildSelectEstablishmentRedirectHref({
          href: '/signals/11111111-1111-4111-8111-111111111111',
        }),
        { replace: true },
      )
    })
    expect(switchEstablishment).not.toHaveBeenCalled()
  })

  it('switches when entering an establishment-scoped route without a session', async () => {
    const bootstrap = bootstrapWithoutActiveMembership()
    authState.bootstrap = bootstrap
    authState.memberships = bootstrap.memberships
    authState.hasOperationalAccess = false
    routeState.route = {
      kind: 'scoped-terrain',
      scope: { type: 'establishment', establishmentId: 'est-2' },
      page: 'signals',
    }

    render(wrapApp())

    await waitFor(() => {
      expect(switchEstablishment).toHaveBeenCalledWith({ establishment_id: 'est-2' })
    })
  })

  it('lands desktop cross users without a session on the cross dashboard', async () => {
    stubLgViewport(true)
    window.history.replaceState(null, '', '/login')
    const bootstrap = bootstrapWithoutActiveMembership()
    authState.bootstrap = bootstrap
    authState.memberships = bootstrap.memberships
    authState.hasOperationalAccess = false
    routeState.route = { kind: 'static', path: '/login' }

    render(wrapApp())

    await waitFor(() => {
      expect(navigate).toHaveBeenCalledWith('/cross/signals', { replace: true })
    })
    expect(switchEstablishment).not.toHaveBeenCalled()
    expect(navigate).not.toHaveBeenCalledWith(
      expect.stringMatching(/^\/select-establishment/),
      expect.anything(),
    )
  })

  it('redirects desktop users away from the establishment selector', async () => {
    stubLgViewport(true)
    const bootstrap = bootstrapWithoutActiveMembership()
    authState.bootstrap = bootstrap
    authState.memberships = bootstrap.memberships
    authState.hasOperationalAccess = false
    routeState.route = { kind: 'static', path: '/select-establishment' }

    render(wrapApp())

    await waitFor(() => {
      expect(navigate).toHaveBeenCalledWith('/cross/signals', { replace: true })
    })
    expect(switchEstablishment).not.toHaveBeenCalled()
  })

  it('silently switches on desktop when a scoped route differs from the session', async () => {
    stubLgViewport(true)
    const bootstrap = bootstrapWithSelectedEstablishment('est-1')
    authState.bootstrap = bootstrap
    authState.memberships = bootstrap.memberships
    authState.hasOperationalAccess = true
    routeState.route = {
      kind: 'scoped-terrain',
      scope: { type: 'establishment', establishmentId: 'est-2' },
      page: 'chat',
    }

    render(wrapApp())

    await waitFor(() => {
      expect(switchEstablishment).toHaveBeenCalledWith({ establishment_id: 'est-2' })
    })
    expect(navigate).not.toHaveBeenCalledWith(
      expect.stringMatching(/^\/select-establishment/),
      expect.anything(),
    )
  })

  it('silently switches on desktop for a scoped signals hub that differs from the session', async () => {
    stubLgViewport(true)
    const bootstrap = bootstrapWithSelectedEstablishment('est-1')
    authState.bootstrap = bootstrap
    authState.memberships = bootstrap.memberships
    authState.hasOperationalAccess = true
    routeState.route = {
      kind: 'scoped-terrain',
      scope: { type: 'establishment', establishmentId: 'est-2' },
      page: 'signals',
    }

    render(wrapApp())

    await waitFor(() => {
      expect(switchEstablishment).toHaveBeenCalledWith({ establishment_id: 'est-2' })
    })
    expect(navigate).not.toHaveBeenCalledWith(
      expect.stringMatching(/^\/select-establishment/),
      expect.anything(),
    )
  })

  it('does not switch when the scoped route already matches the session', async () => {
    stubLgViewport(true)
    const bootstrap = bootstrapWithSelectedEstablishment('est-2')
    authState.bootstrap = bootstrap
    authState.memberships = bootstrap.memberships
    authState.hasOperationalAccess = true
    routeState.route = {
      kind: 'scoped-terrain',
      scope: { type: 'establishment', establishmentId: 'est-2' },
      page: 'signals',
    }

    render(wrapApp())

    expect(switchEstablishment).not.toHaveBeenCalled()
    expect(navigate).not.toHaveBeenCalled()
  })

  it('does not switch on a session-scoped chat route', async () => {
    stubLgViewport(true)
    const bootstrap = bootstrapWithSelectedEstablishment('est-1')
    authState.bootstrap = bootstrap
    authState.memberships = bootstrap.memberships
    authState.hasOperationalAccess = true
    routeState.route = { kind: 'static', path: '/chat' }

    render(wrapApp())

    expect(switchEstablishment).not.toHaveBeenCalled()
  })

  it('does not switch on a cross route', async () => {
    stubLgViewport(true)
    const bootstrap = bootstrapWithSelectedEstablishment('est-1')
    authState.bootstrap = bootstrap
    authState.memberships = bootstrap.memberships
    authState.hasOperationalAccess = true
    routeState.route = {
      kind: 'scoped-terrain',
      scope: { type: 'cross' },
      page: 'signals',
    }

    render(wrapApp())

    expect(switchEstablishment).not.toHaveBeenCalled()
    expect(navigate).not.toHaveBeenCalled()
  })

  it('does not switch a scoped route the user cannot join', async () => {
    stubLgViewport(true)
    const bootstrap = bootstrapWithSelectedEstablishment('est-1')
    authState.bootstrap = bootstrap
    authState.memberships = bootstrap.memberships
    authState.hasOperationalAccess = true
    routeState.route = {
      kind: 'scoped-terrain',
      scope: { type: 'establishment', establishmentId: 'est-unknown' },
      page: 'signals',
    }

    render(wrapApp())

    expect(switchEstablishment).not.toHaveBeenCalled()
    expect(navigate).not.toHaveBeenCalledWith(
      expect.stringMatching(/^\/select-establishment/),
      expect.anything(),
    )
  })

  it('sends a mobile scoped mismatch to the selector without switching', async () => {
    stubLgViewport(false)
    const bootstrap = bootstrapWithSelectedEstablishment('est-1')
    authState.bootstrap = bootstrap
    authState.memberships = bootstrap.memberships
    authState.hasOperationalAccess = true
    routeState.route = {
      kind: 'scoped-terrain',
      scope: { type: 'establishment', establishmentId: 'est-2' },
      page: 'chat',
    }

    render(wrapApp())

    await waitFor(() => {
      expect(navigate).toHaveBeenCalledWith(
        buildSelectEstablishmentRedirectHref({
          href: '/e/est-2/chat',
          establishmentId: 'est-2',
        }),
        { replace: true },
      )
    })
    expect(switchEstablishment).not.toHaveBeenCalled()
  })

  it('redirects operational desktop web users away from the establishment selector', async () => {
    stubLgViewport(true)
    const active = membership('membership-1', 'est-1', 'owner')
    const bootstrap = bootstrapWithoutActiveMembership({
      memberships: [active],
      active_membership: active,
      permission_hints: {
        chat_available: false,
        can_create_action_plan: false,
        can_create_catalog_action_plan: false,
        can_view_action_plan_catalog: false,
        can_invite: false,
        can_manage_runtime_config: false,
        can_view_team: false,
        can_manage_organization: true,
        platform_operator_active: false,
      },
    })
    authState.bootstrap = bootstrap
    authState.memberships = bootstrap.memberships
    authState.hasOperationalAccess = true
    routeState.route = { kind: 'static', path: '/select-establishment' }

    render(wrapApp())

    await waitFor(() => {
      expect(navigate).toHaveBeenCalledWith('/reporting', { replace: true })
    })
    expect(switchEstablishment).not.toHaveBeenCalled()
  })

  it('falls back to the desktop landing when a selector hint cannot be opened', async () => {
    stubLgViewport(true)
    switchEstablishment.mockRejectedValue(new Error('cannot open'))
    window.history.replaceState(
      null,
      '',
      '/select-establishment?next=/signals/s1&establishment_id=est-2',
    )
    const bootstrap = bootstrapWithoutActiveMembership()
    authState.bootstrap = bootstrap
    authState.memberships = bootstrap.memberships
    authState.hasOperationalAccess = false
    routeState.route = { kind: 'static', path: '/select-establishment' }

    render(wrapApp())

    await waitFor(() => {
      expect(switchEstablishment).toHaveBeenCalledWith({ establishment_id: 'est-2' })
      expect(navigate).toHaveBeenCalledWith('/cross/signals', { replace: true })
    })
  })

  it('keeps operational mobile users on the selector even with an establishment hint', async () => {
    stubLgViewport(false)
    window.history.replaceState(
      null,
      '',
      '/select-establishment?next=/signals/s1&establishment_id=est-2',
    )
    const bootstrap = bootstrapWithSelectedEstablishment('est-1')
    authState.bootstrap = bootstrap
    authState.memberships = bootstrap.memberships
    authState.hasOperationalAccess = true
    routeState.route = { kind: 'static', path: '/select-establishment' }

    render(wrapApp())

    expect(await screen.findByTestId('select-establishment-page')).toBeTruthy()
    expect(switchEstablishment).not.toHaveBeenCalled()
    expect(navigate).not.toHaveBeenCalled()
  })

  it('keeps operational mobile users on the selector without a hint', async () => {
    stubLgViewport(false)
    const bootstrap = bootstrapWithSelectedEstablishment('est-1')
    authState.bootstrap = bootstrap
    authState.memberships = bootstrap.memberships
    authState.hasOperationalAccess = true
    routeState.route = { kind: 'static', path: '/select-establishment' }

    render(wrapApp())

    expect(await screen.findByTestId('select-establishment-page')).toBeTruthy()
    expect(navigate).not.toHaveBeenCalled()
  })

  it('does not auto-open a hinted establishment for operational native users on a large viewport', async () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    stubLgViewport(true)
    window.history.replaceState(
      null,
      '',
      '/select-establishment?next=/signals/s1&establishment_id=est-2',
    )
    const bootstrap = bootstrapWithSelectedEstablishment('est-1')
    authState.bootstrap = bootstrap
    authState.memberships = bootstrap.memberships
    authState.hasOperationalAccess = true
    routeState.route = { kind: 'static', path: '/select-establishment' }

    render(wrapApp())

    expect(await screen.findByTestId('select-establishment-page')).toBeTruthy()
    expect(switchEstablishment).not.toHaveBeenCalled()
    expect(navigate).not.toHaveBeenCalled()
  })

  it('keeps native large-viewport users on the selector without operational access', async () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    stubLgViewport(true)
    const bootstrap = bootstrapWithoutActiveMembership()
    authState.bootstrap = bootstrap
    authState.memberships = bootstrap.memberships
    authState.hasOperationalAccess = false
    routeState.route = { kind: 'static', path: '/select-establishment' }

    render(wrapApp())

    expect(await screen.findByTestId('select-establishment-page')).toBeTruthy()
    expect(navigate).not.toHaveBeenCalledWith('/cross/signals', { replace: true })
    expect(switchEstablishment).not.toHaveBeenCalled()
  })

  it('lands authenticated native login on the mobile selector even on a large viewport', async () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    stubLgViewport(true)
    window.history.replaceState(null, '', '/login')
    const bootstrap = bootstrapWithoutActiveMembership()
    authState.bootstrap = bootstrap
    authState.memberships = bootstrap.memberships
    authState.hasOperationalAccess = false
    routeState.route = { kind: 'static', path: '/login' }

    render(wrapApp())

    await waitFor(() => {
      expect(navigate).toHaveBeenCalledWith('/select-establishment', { replace: true })
    })
    expect(navigate).not.toHaveBeenCalledWith('/cross/signals', { replace: true })
  })

  it('silently switches on desktop when operational config differs from the session', async () => {
    stubLgViewport(true)
    const bootstrap = bootstrapWithSelectedEstablishment('est-1')
    authState.bootstrap = bootstrap
    authState.memberships = bootstrap.memberships
    authState.hasOperationalAccess = true
    routeState.route = {
      kind: 'scoped-terrain',
      scope: { type: 'establishment', establishmentId: 'est-2' },
      page: 'operational-config',
    }

    render(wrapApp())

    await waitFor(() => {
      expect(switchEstablishment).toHaveBeenCalledWith({ establishment_id: 'est-2' })
    })
    expect(navigate).not.toHaveBeenCalledWith(
      expect.stringMatching(/^\/select-establishment/),
      expect.anything(),
    )
  })

  it('redirects web mobile operational-config to reporting without mounting the editor', async () => {
    stubLgViewport(false)
    const bootstrap = bootstrapWithSelectedEstablishment('est-2')
    authState.bootstrap = bootstrap
    authState.memberships = bootstrap.memberships
    authState.hasOperationalAccess = true
    routeState.route = {
      kind: 'scoped-terrain',
      scope: { type: 'establishment', establishmentId: 'est-2' },
      page: 'operational-config',
    }

    render(wrapApp())

    await waitFor(() => {
      expect(navigate).toHaveBeenCalledWith('/e/est-2/reporting', { replace: true })
    })
    expect(screen.queryByTestId('operational-config')).toBeNull()
    expect(switchEstablishment).not.toHaveBeenCalled()
  })

  it('redirects native large-viewport operational-config to reporting', async () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    stubLgViewport(true)
    const bootstrap = bootstrapWithSelectedEstablishment('est-2')
    authState.bootstrap = bootstrap
    authState.memberships = bootstrap.memberships
    authState.hasOperationalAccess = true
    routeState.route = {
      kind: 'scoped-terrain',
      scope: { type: 'establishment', establishmentId: 'est-2' },
      page: 'operational-config',
    }

    render(wrapApp())

    await waitFor(() => {
      expect(navigate).toHaveBeenCalledWith('/e/est-2/reporting', { replace: true })
    })
    expect(screen.queryByTestId('operational-config')).toBeNull()
    expect(switchEstablishment).not.toHaveBeenCalled()
  })

  it('redirects web mobile /platform without mounting PlatformShell', async () => {
    stubLgViewport(false)
    const bootstrap = bootstrapWithoutActiveMembership({
      memberships: [],
      permission_hints: {
        chat_available: false,
        can_create_action_plan: false,
        can_create_catalog_action_plan: false,
        can_view_action_plan_catalog: false,
        can_invite: false,
        can_manage_runtime_config: false,
        can_view_team: false,
        can_manage_organization: false,
        platform_operator_active: true,
      },
    })
    authState.bootstrap = bootstrap
    authState.memberships = []
    authState.hasOperationalAccess = false
    routeState.route = { kind: 'platform', section: 'onboardings' }

    render(wrapApp())

    await waitFor(() => {
      expect(navigate).toHaveBeenCalledWith('/no-establishment', { replace: true })
    })
    expect(screen.queryByTestId('platform-shell')).toBeNull()
  })

  it('mounts PlatformShell on desktop web for an operator without membership', async () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'web')
    stubLgViewport(true)
    const bootstrap = bootstrapWithoutActiveMembership({
      memberships: [],
      permission_hints: {
        chat_available: false,
        can_create_action_plan: false,
        can_create_catalog_action_plan: false,
        can_view_action_plan_catalog: false,
        can_invite: false,
        can_manage_runtime_config: false,
        can_view_team: false,
        can_manage_organization: false,
        platform_operator_active: true,
      },
    })
    authState.bootstrap = bootstrap
    authState.memberships = []
    authState.hasOperationalAccess = false
    routeState.route = { kind: 'platform', section: 'onboardings' }

    render(wrapApp())

    expect(await screen.findByTestId('platform-shell')).toBeTruthy()
    expect(navigate).not.toHaveBeenCalled()
  })
})
