// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { AppRoute } from '@/app/app-routes'
import { getAuthenticatedLandingPath } from '@/features/auth/lib/authenticated-landing'
import type { BootstrapResponse, Membership } from '@/features/auth/types'

const navigate = vi.fn()
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
  const buildSignalPlanPath = (
    signalId: string,
    context?: {
      patternId: string
      state: {
        periodStart: string
        periodEnd: string
        organizationId: string | null
        q: string
        recurrence: string
      }
    } | null,
  ) => {
    if (!context) {
      return `/signals/${signalId}/plan`
    }
    const params = new URLSearchParams()
    params.set('period_start', context.state.periodStart)
    params.set('period_end', context.state.periodEnd)
    if (context.state.organizationId) {
      params.set('organization_id', context.state.organizationId)
    }
    if (context.state.q) {
      params.set('q', context.state.q)
    }
    if (context.state.recurrence !== 'all') {
      params.set('recurrence', context.state.recurrence)
    }
    params.set('analytics_pattern_id', context.patternId)
    return `/signals/${signalId}/plan?${params.toString()}`
  }
  return {
    LazyActionPlanCreatePage: ({ backPath }: { backPath?: string }) =>
      createElement('div', { 'data-testid': 'action-plan-create', 'data-back-path': backPath }, 'action-plan-create'),
    LazyActionPlanExecutionDetailPage: () => createElement(Page, { name: 'execution-detail' }),
    LazyActionPlanExecutionEditPage: () => createElement(Page, { name: 'execution-edit' }),
    LazyActionPlanHubPage: () => createElement(Page, { name: 'action-plan-hub' }),
    LazyActionPlanTemplateDetailPage: () => createElement(Page, { name: 'template-detail' }),
    LazyAnalyticsPage: () => createElement(Page, { name: 'analytics' }),
    LazyAnalyticsPatternDetailPage: () => createElement(Page, { name: 'analytics-pattern-detail' }),
    LazyChatConversationPage: () => createElement(Page, { name: 'chat-conversation' }),
    LazyChatPage: () => createElement(Page, { name: 'chat' }),
    LazyChatRealtimeProvider: ({ children }: { children: React.ReactNode }) => children,
    LazyExecutionFeedPage: () => createElement(Page, { name: 'execution' }),
    LazyExecutionUpcomingPage: () => createElement(Page, { name: 'execution-upcoming' }),
    LazyInstallAppPage: () => createElement(Page, { name: 'install-app' }),
    LazyNotificationsCenterPage: () => createElement(Page, { name: 'notifications' }),
    LazyProfilePage: () => createElement(Page, { name: 'profile' }),
    LazyProfileSwitchEstablishmentPage: () => createElement(Page, { name: 'switch-establishment' }),
    LazyReportPage: () => createElement(Page, { name: 'reporting' }),
    LazySignalDetailPage: ({
      signalId,
      analyticsSignalReturnContext,
    }: {
      signalId: string
      analyticsSignalReturnContext?: {
        patternId: string
        state: {
          periodStart: string
          periodEnd: string
          organizationId: string | null
          q: string
          recurrence: string
        }
      } | null
    }) =>
      createElement(
        'div',
        {
          'data-testid': 'signal-detail',
          'data-plan-path': buildSignalPlanPath(signalId, analyticsSignalReturnContext),
        },
        'signal-detail',
      ),
    LazySignalFeedPage: () => createElement(Page, { name: 'signals' }),
    LazyTeamMemberDetailPage: () => createElement(Page, { name: 'team-member' }),
    LazyTeamPage: () => createElement(Page, { name: 'team' }),
  }
})

vi.mock('@/components/layout/pwa-update-banner', () => ({
  PwaUpdateBanner: () => null,
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
      can_create_establishment: false,
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

afterEach(() => {
  cleanup()
  navigate.mockReset()
  routeState.route = { kind: 'static', path: '/analytics' }
  authState.bootstrap = null
  authState.hasOperationalAccess = false
  authState.memberships = []
  authState.pendingOnboardingMemberships = []
})

describe('App terrain active membership routing', () => {
  it('keeps analytics available without active membership and redirects reporting to selection', async () => {
    const bootstrap = bootstrapWithoutActiveMembership()
    authState.bootstrap = bootstrap
    authState.memberships = bootstrap.memberships
    authState.hasOperationalAccess = false

    const rendered = render(createElement(App))

    expect(navigate).not.toHaveBeenCalled()

    routeState.route = { kind: 'static', path: '/reporting' }
    rendered.rerender(createElement(App))

    await waitFor(() => {
      expect(navigate).toHaveBeenCalledWith('/select-establishment', { replace: true })
    })
  })

  it('sends analytics Back to /general when operational access is available', () => {
    const bootstrap = bootstrapWithActiveMembership()
    authState.bootstrap = bootstrap
    authState.memberships = bootstrap.memberships
    authState.hasOperationalAccess = true

    render(createElement(App))

    fireEvent.click(screen.getByRole('button', { name: 'Retour' }))

    expect(navigate).toHaveBeenCalledWith('/general')
  })

  it('sends analytics Back to authenticated landing without active membership', () => {
    const bootstrap = bootstrapWithoutActiveMembership()
    authState.bootstrap = bootstrap
    authState.memberships = bootstrap.memberships
    authState.hasOperationalAccess = false

    render(createElement(App))

    fireEvent.click(screen.getByRole('button', { name: 'Retour' }))

    expect(navigate).toHaveBeenCalledWith(getAuthenticatedLandingPath(bootstrap))
    expect(navigate).toHaveBeenCalledWith('/select-establishment')
    expect(navigate).not.toHaveBeenCalledWith('/general')
  })

  it('sends analytics Back to organization landing for org managers without selection', () => {
    const bootstrap = bootstrapWithoutActiveMembership({
      permission_hints: {
        chat_available: false,
        can_create_action_plan: false,
        can_create_catalog_action_plan: false,
        can_view_action_plan_catalog: false,
        can_invite: false,
        can_manage_runtime_config: false,
        can_view_team: false,
        can_manage_organization: true,
        can_create_establishment: true,
      },
    })
    authState.bootstrap = bootstrap
    authState.memberships = bootstrap.memberships
    authState.hasOperationalAccess = false

    render(createElement(App))

    fireEvent.click(screen.getByRole('button', { name: 'Retour' }))

    expect(navigate).toHaveBeenCalledWith(getAuthenticatedLandingPath(bootstrap))
    expect(navigate).toHaveBeenCalledWith('/organization')
    expect(navigate).not.toHaveBeenCalledWith('/general')
  })

  it('sends analytics pattern detail Back to the resolved Analytics URL state', () => {
    const bootstrap = bootstrapWithoutActiveMembership()
    authState.bootstrap = bootstrap
    authState.memberships = bootstrap.memberships
    authState.hasOperationalAccess = false
    routeState.route = { kind: 'analytics-pattern-detail', patternId: 'pattern-1' }
    window.history.replaceState(
      null,
      '',
      '/analytics/patterns/pattern-1?period_start=2026-07-01T00%3A00%3A00.000Z&period_end=2026-08-01T00%3A00%3A00.000Z&q=retard&recurrence=recurrent',
    )

    render(createElement(App))

    fireEvent.click(screen.getByRole('button', { name: 'Retour' }))

    expect(navigate).toHaveBeenCalledWith(
      '/analytics?period_start=2026-07-01T00%3A00%3A00.000Z&period_end=2026-08-01T00%3A00%3A00.000Z&q=retard&recurrence=recurrent',
    )
  })

  it('sends Signal Back to the Analytics pattern detail when Analytics context is present', () => {
    const bootstrap = bootstrapWithActiveMembership()
    authState.bootstrap = bootstrap
    authState.memberships = bootstrap.memberships
    authState.hasOperationalAccess = true
    routeState.route = {
      kind: 'signal-detail',
      signalId: '55555555-5555-4555-8555-555555555555',
    }
    window.history.replaceState(
      null,
      '',
      '/signals/55555555-5555-4555-8555-555555555555?period_start=2026-07-01T00%3A00%3A00.000Z&period_end=2026-08-01T00%3A00%3A00.000Z&q=retard&recurrence=recurrent&analytics_pattern_id=44444444-4444-4444-8444-444444444444',
    )

    render(createElement(App))

    fireEvent.click(screen.getByRole('button', { name: 'Retour' }))

    expect(navigate).toHaveBeenCalledWith(
      '/analytics/patterns/44444444-4444-4444-8444-444444444444?period_start=2026-07-01T00%3A00%3A00.000Z&period_end=2026-08-01T00%3A00%3A00.000Z&q=retard&recurrence=recurrent',
    )
  })

  it('shares one stable default Analytics period between Signal Back and Plan creation links', () => {
    const bootstrap = bootstrapWithActiveMembership()
    authState.bootstrap = bootstrap
    authState.memberships = bootstrap.memberships
    authState.hasOperationalAccess = true
    routeState.route = {
      kind: 'signal-detail',
      signalId: '55555555-5555-4555-8555-555555555555',
    }
    window.history.replaceState(
      null,
      '',
      '/signals/55555555-5555-4555-8555-555555555555?analytics_pattern_id=44444444-4444-4444-8444-444444444444',
    )

    const rendered = render(createElement(App))

    const planPath = screen.getByTestId('signal-detail').getAttribute('data-plan-path') ?? ''
    fireEvent.click(screen.getByRole('button', { name: 'Retour' }))
    const backPath = navigate.mock.calls[0]?.[0] as string
    const backParams = new URL(backPath, 'https://spore.test').searchParams
    const planParams = new URL(planPath, 'https://spore.test').searchParams

    expect(planParams.get('period_start')).toBe(backParams.get('period_start'))
    expect(planParams.get('period_end')).toBe(backParams.get('period_end'))
    expect(planParams.get('analytics_pattern_id')).toBe(
      '44444444-4444-4444-8444-444444444444',
    )

    rendered.rerender(createElement(App))

    const rerenderedPlanPath =
      screen.getByTestId('signal-detail').getAttribute('data-plan-path') ?? ''
    const rerenderedPlanParams = new URL(rerenderedPlanPath, 'https://spore.test').searchParams
    expect(rerenderedPlanParams.get('period_start')).toBe(planParams.get('period_start'))
    expect(rerenderedPlanParams.get('period_end')).toBe(planParams.get('period_end'))
  })

  it('keeps direct Signal Back on the Signal feed without Analytics context', () => {
    const bootstrap = bootstrapWithActiveMembership()
    authState.bootstrap = bootstrap
    authState.memberships = bootstrap.memberships
    authState.hasOperationalAccess = true
    routeState.route = {
      kind: 'signal-detail',
      signalId: '55555555-5555-4555-8555-555555555555',
    }
    window.history.replaceState(null, '', '/signals/55555555-5555-4555-8555-555555555555')

    render(createElement(App))

    fireEvent.click(screen.getByRole('button', { name: 'Retour' }))

    expect(navigate).toHaveBeenCalledWith('/signals')
  })

  it('passes Analytics Signal context as the Plan creation back path', () => {
    const bootstrap = bootstrapWithActiveMembership()
    authState.bootstrap = bootstrap
    authState.memberships = bootstrap.memberships
    authState.hasOperationalAccess = true
    routeState.route = {
      kind: 'signal-action-create',
      signalId: '55555555-5555-4555-8555-555555555555',
    }
    window.history.replaceState(
      null,
      '',
      '/signals/55555555-5555-4555-8555-555555555555/plan?period_start=2026-07-01T00%3A00%3A00.000Z&period_end=2026-08-01T00%3A00%3A00.000Z&q=retard&recurrence=recurrent&analytics_pattern_id=44444444-4444-4444-8444-444444444444',
    )

    render(createElement(App))

    expect(screen.getByTestId('action-plan-create').getAttribute('data-back-path')).toBe(
      '/signals/55555555-5555-4555-8555-555555555555?period_start=2026-07-01T00%3A00%3A00.000Z&period_end=2026-08-01T00%3A00%3A00.000Z&q=retard&recurrence=recurrent&analytics_pattern_id=44444444-4444-4444-8444-444444444444',
    )
  })

  it('keeps direct Signal Plan creation back path without Analytics context', () => {
    const bootstrap = bootstrapWithActiveMembership()
    authState.bootstrap = bootstrap
    authState.memberships = bootstrap.memberships
    authState.hasOperationalAccess = true
    routeState.route = {
      kind: 'signal-action-create',
      signalId: '55555555-5555-4555-8555-555555555555',
    }
    window.history.replaceState(
      null,
      '',
      '/signals/55555555-5555-4555-8555-555555555555/plan',
    )

    render(createElement(App))

    expect(screen.getByTestId('action-plan-create').getAttribute('data-back-path')).toBe(
      '/signals/55555555-5555-4555-8555-555555555555',
    )
  })
})
