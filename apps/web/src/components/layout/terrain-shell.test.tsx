// @vitest-environment jsdom

import { createElement, type ComponentProps } from 'react'
import { cleanup, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { TerrainShell } from '@/components/layout/terrain-shell'
import type { BootstrapResponse, Membership } from '@/features/auth/types'

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
      can_create_establishment: false,
    },
  }
}

function renderTerrainShell(
  mainScroll: 'auto' | 'hidden' = 'hidden',
  options: Partial<ComponentProps<typeof TerrainShell>> = {},
) {
  return render(
    createElement(
      TerrainShell,
      {
        contentKey: 'test',
        topbar: <div data-testid="terrain-topbar">Topbar</div>,
        showBottomNav: false,
        mainScroll,
        navigate: () => undefined,
        ...options,
      },
      <div data-testid="page-content">Page</div>,
    ),
  )
}

afterEach(() => {
  cleanup()
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
      'pt-[env(safe-area-inset-top)]',
    )
    unmount()

    renderTerrainShell('auto')
    expect(screen.getByRole('main').className).not.toContain(
      'pt-[env(safe-area-inset-top)]',
    )
  })

  it('renders one shared topbar and a desktop sidebar from shared navigation', () => {
    renderTerrainShell('auto', {
      bootstrap: bootstrap([membership({ role: 'manager' })]),
      desktopActivePath: '/analytics',
      showChatNav: false,
    })

    expect(screen.getAllByTestId('terrain-topbar')).toHaveLength(1)
    const sidebar = screen.getByLabelText('Navigation principale')
    expect(within(sidebar).getByRole('link', { name: 'Nouvelle observation' })).toBeTruthy()
    expect(within(sidebar).getByRole('link', { name: 'Analyse' }).getAttribute('aria-current'))
      .toBe('page')
    expect(within(sidebar).queryByRole('link', { name: 'Chat' })).toBeNull()
    expect(within(sidebar).getByText('Marie Renaud')).toBeTruthy()
    expect(within(sidebar).getByText('Manager · Spore Paris')).toBeTruthy()
  })

  it('keeps Analytics out of the desktop sidebar for Staff-only users', () => {
    renderTerrainShell('auto', {
      bootstrap: bootstrap([membership({ role: 'staff' })]),
      desktopActivePath: '/general',
      showChatNav: true,
    })

    const sidebar = screen.getByLabelText('Navigation principale')
    expect(within(sidebar).queryByRole('link', { name: 'Analyse' })).toBeNull()
    expect(within(sidebar).getByRole('link', { name: 'Chat' })).toBeTruthy()
  })

  it('keeps bottom navigation mobile-only when enabled', () => {
    renderTerrainShell('auto', {
      activeNavPath: '/signals',
      showBottomNav: true,
    })

    const bottomNav = screen.getByRole('navigation', { name: 'Navigation terrain' })
    expect(bottomNav.className).toContain('lg:hidden')
  })

  it('scopes toast and processing overlays to the content column beside the sidebar', () => {
    renderTerrainShell('auto', {
      bootstrap: bootstrap([membership({ role: 'manager' })]),
      desktopActivePath: '/analytics',
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
})
