// @vitest-environment jsdom

import { createElement, type ComponentProps } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { AppRoute } from '@/app/app-routes'
import { TerrainShell } from '@/components/layout/terrain-shell'
import { TerrainTopbar } from '@/components/layout/terrain-topbar'
import type { BootstrapResponse, Membership } from '@/features/auth/types'

const mockNativeKeyboardOpen = vi.hoisted(() => ({ current: false }))
const { lgViewportState } = vi.hoisted(() => ({
  lgViewportState: { current: false },
}))

vi.mock('@/lib/lg-viewport', () => ({
  useLgViewport: () => lgViewportState.current,
}))

vi.mock('@/components/layout/network-status-banner', () => ({
  NetworkStatusBanner: () => null,
}))

vi.mock('@/features/realtime/components/operational-reconnect-banner', () => ({
  OperationalReconnectBanner: () => null,
}))

vi.mock('@/features/realtime/components/operational-realtime-provider', () => ({
  useOptionalOperationalRealtime: () => null,
}))

vi.mock('@/lib/network-status', () => ({
  useNetworkStatus: () => ({ isOnline: true }),
}))

vi.mock('@/lib/native-keyboard', () => ({
  useNativeKeyboardOpen: () => mockNativeKeyboardOpen.current,
}))

vi.mock('framer-motion', () => ({
  AnimatePresence: ({ children }: { children: React.ReactNode }) => children,
  motion: {
    div: ({ children, className }: { children: React.ReactNode; className?: string }) => (
      <div className={className}>{children}</div>
    ),
  },
  useReducedMotion: () => true,
}))

function membership(overrides: Partial<Membership>): Membership {
  return {
    id: overrides.id ?? `membership-${overrides.role ?? 'staff'}`,
    establishment_id: overrides.establishment_id ?? 'est-1',
    establishment_name: overrides.establishment_name ?? 'Spore Paris',
    organization_id: overrides.organization_id ?? 'org-1',
    organization_name: overrides.organization_name ?? 'Spore',
    role: overrides.role ?? 'staff',
    status: overrides.status ?? 'active',
    chat_available: overrides.chat_available ?? true,
    scopes: [],
    scope_summary: { business_unit_count: 0 },
  }
}

function bootstrap(memberships: Membership[]): BootstrapResponse {
  const activeMembership = memberships[0] ?? null

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
    active_membership: activeMembership,
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
  }
}

function renderTerrainShell(
  mainScroll: 'auto' | 'hidden' = 'hidden',
  options: Partial<ComponentProps<typeof TerrainShell>> = {},
) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })

  return render(
    createElement(
      QueryClientProvider,
      { client },
      createElement(
        TerrainShell,
        {
          contentKey: 'test',
          topbar: <div data-testid="terrain-topbar">Topbar</div>,
          showBottomNav: false,
          mainScroll,
          route: { kind: 'static', path: '/general' } satisfies AppRoute,
          navigate: () => undefined,
          ...options,
        },
        <div data-testid="page-content">Page</div>,
      ),
    ),
  )
}

afterEach(() => {
  cleanup()
  mockNativeKeyboardOpen.current = false
  lgViewportState.current = false
  vi.unstubAllEnvs()
})

describe('TerrainShell', () => {
  it('locks main scroll when mainScroll is hidden', () => {
    renderTerrainShell('hidden')

    const main = screen.getByRole('main')
    expect(main.className).toContain('overflow-hidden')
    expect(main.className).not.toContain('overflow-y-auto')

    const contentColumn = main.parentElement
    const shell = contentColumn?.parentElement
    expect(shell?.className).toContain('fixed')
    expect(shell?.className).toContain('h-dvh')
    expect(shell?.className).toContain('overflow-hidden')
    expect(shell?.getAttribute('data-terrain-shell-root')).not.toBeNull()
  })

  it('allows main scroll when mainScroll is auto', () => {
    renderTerrainShell('auto')

    const main = screen.getByRole('main')
    expect(main.className).toContain('overflow-y-auto')
  })

  it('owns top safe-area on main only when the topbar is absent', () => {
    const { unmount } = renderTerrainShell('auto', { topbar: null })

    expect(screen.getByRole('main').className).toContain(
      'pt-[var(--app-safe-top)]',
    )
    unmount()

    renderTerrainShell('auto')
    expect(screen.getByRole('main').className).not.toContain(
      'pt-[var(--app-safe-top)]',
    )
  })

  it('renders one shared topbar and a desktop sidebar from shared navigation', () => {
    lgViewportState.current = true
    renderTerrainShell('auto', {
      bootstrap: bootstrap([membership({ role: 'manager' })]),
    })

    expect(screen.getAllByTestId('terrain-topbar')).toHaveLength(1)
    const sidebar = screen.getByLabelText('Navigation principale')
    expect(within(sidebar).queryByText('Cross-établissement')).toBeNull()
    expect(within(sidebar).getByRole('link', { name: 'Nouvelle observation' })).toBeTruthy()
    expect(within(sidebar).getByRole('link', { name: 'Dashboard' })).toBeTruthy()
    expect(within(sidebar).getByRole('link', { name: 'Chat' })).toBeTruthy()
    expect(within(sidebar).getByText('Marie Renaud')).toBeTruthy()
    expect(within(sidebar).getByText('Manager · Spore Paris')).toBeTruthy()
  })

  it('keeps Analytics out of the desktop sidebar for Staff-only users', () => {
    lgViewportState.current = true
    renderTerrainShell('auto', {
      bootstrap: bootstrap([membership({ role: 'staff' })]),
    })

    const sidebar = screen.getByLabelText('Navigation principale')
    expect(within(sidebar).queryByRole('link', { name: 'Analyse' })).toBeNull()
    expect(within(sidebar).queryByRole('link', { name: 'Dashboard' })).toBeNull()
  })

  it('always shows Chat in the mobile bottom nav', () => {
    renderTerrainShell('auto', {
      activeNavPath: '/signals',
      showBottomNav: true,
    })

    expect(screen.getByRole('link', { name: 'Chat' })).toBeTruthy()
    const shell = screen.getByRole('main').closest('[data-terrain-shell-root]')
    expect(shell?.className).not.toContain('app-safe-left')
    expect(shell?.className).not.toContain('--app-safe-left')
  })

  it('keeps bottom navigation on mobile web and hides it on desktop web', () => {
    const { unmount } = renderTerrainShell('auto', {
      activeNavPath: '/signals',
      showBottomNav: true,
    })

    const bottomNav = screen.getByRole('navigation', { name: 'Navigation terrain' })
    expect(bottomNav.className).not.toContain('lg:hidden')
    expect(screen.queryByLabelText('Navigation principale')).toBeNull()
    const shell = screen.getByRole('main').closest('[data-terrain-shell-root]')
    expect(shell?.className).toContain('max-w-md')
    expect(shell?.className).not.toContain('max-w-none')
    unmount()

    lgViewportState.current = true
    renderTerrainShell('auto', {
      activeNavPath: '/signals',
      showBottomNav: true,
      bootstrap: bootstrap([membership({ role: 'staff' })]),
    })
    expect(screen.queryByRole('navigation', { name: 'Navigation terrain' })).toBeNull()
    expect(screen.getByLabelText('Navigation principale')).toBeTruthy()
    expect(screen.getByRole('main').closest('[data-terrain-shell-root]')?.className).toContain(
      'max-w-none',
    )
  })

  it('keeps the mobile shell on native at a large viewport', () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    lgViewportState.current = true
    renderTerrainShell('auto', {
      activeNavPath: '/signals',
      showBottomNav: true,
      bootstrap: bootstrap([membership({ role: 'staff' })]),
      topbar: <TerrainTopbar variant="hub" pageTitle="Observations" />,
    })

    expect(screen.queryByLabelText('Navigation principale')).toBeNull()
    expect(screen.getByRole('navigation', { name: 'Navigation terrain' })).toBeTruthy()
    const shell = screen.getByRole('main').closest('[data-terrain-shell-root]')
    expect(shell?.className).toContain('max-w-md')
    expect(shell?.className).toContain('flex-col')
    expect(shell?.className).not.toContain('flex-row')
    const topbar = screen.getByRole('banner')
    expect(topbar.className).toContain('pt-[max(0.75rem,var(--app-safe-top))]')
    expect(topbar.className).not.toContain('pt-0')
  })

  it('hides bottom navigation while the native keyboard is open', () => {
    mockNativeKeyboardOpen.current = true
    renderTerrainShell('auto', {
      showBottomNav: true,
    })

    expect(screen.queryByRole('navigation', { name: 'Navigation terrain' })).toBeNull()
  })

  it('shows the shared mobile nav on a destination page without marking a tab current', () => {
    renderTerrainShell('auto', {
      showBottomNav: true,
    })

    const bottomNav = screen.getByRole('navigation', { name: 'Navigation terrain' })
    expect(bottomNav).toBeTruthy()
    expect(screen.queryByRole('link', { current: 'page' })).toBeNull()
    expect(screen.queryByRole('link', { name: 'Analyse' })).toBeNull()
  })

  it('scopes toast and processing overlays to the content column beside the sidebar', () => {
    lgViewportState.current = true
    renderTerrainShell('auto', {
      bootstrap: bootstrap([membership({ role: 'manager' })]),
    })

    const shell = screen.getByRole('main').closest('[data-terrain-shell-root]')
    const sidebar = screen.getByLabelText('Navigation principale')
    const contentColumn = screen.getByRole('main').parentElement
    const overlayHost = contentColumn?.querySelector('.pointer-events-none.absolute')

    expect(shell).toBeTruthy()
    expect(contentColumn?.className).toContain('relative')
    expect(overlayHost).toBeTruthy()
    expect(contentColumn?.contains(overlayHost)).toBe(true)
    expect(sidebar.contains(overlayHost)).toBe(false)
    expect(shell?.contains(sidebar)).toBe(true)
    expect(contentColumn?.parentElement).toBe(shell)
    expect(sidebar.parentElement).toBe(shell)
  })

  it('keeps the sidebar collapsed across terrain page changes', () => {
    lgViewportState.current = true
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    })
    const tree = (contentKey: string) =>
      createElement(
        QueryClientProvider,
        { client },
        createElement(
          TerrainShell,
          {
            contentKey,
            topbar: createElement('div'),
            showBottomNav: false,
            route: { kind: 'static', path: '/general' },
            navigate: () => undefined,
            bootstrap: bootstrap([membership({ role: 'manager' })]),
          },
          createElement('div', null, contentKey),
        ),
      )
    const view = render(tree('signals'))
    fireEvent.click(screen.getByRole('button', { name: 'Réduire la navigation' }))
    view.rerender(tree('execution'))
    expect(screen.getByLabelText('Navigation principale').getAttribute('data-collapsed')).toBe(
      'true',
    )
    expect(screen.getByText('execution')).toBeTruthy()
  })
})
