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
    LazySignalDetailPage: () => createElement(Page, { name: 'signal-detail' }),
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
})
