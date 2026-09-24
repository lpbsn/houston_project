// @vitest-environment jsdom

import { createElement, type ComponentProps, type ReactNode } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { AppRoute } from '@/app/app-routes'
import { DesktopTerrainSidebar } from '@/components/layout/desktop-terrain-sidebar'
import type { BootstrapResponse, Membership } from '@/features/auth/types'

const { lgViewportState } = vi.hoisted(() => ({
  lgViewportState: { current: false },
}))

vi.mock('@/lib/lg-viewport', () => ({
  useLgViewport: () => lgViewportState.current,
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

function bootstrap(
  memberships: Membership[],
  hints: Partial<BootstrapResponse['permission_hints']> = {},
  activeMembership: Membership | null = memberships[0] ?? null,
): BootstrapResponse {
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
      ...hints,
    },
  }
}

function renderSidebar(ui: ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(createElement(QueryClientProvider, { client }, ui))
}

function sidebarProps(
  overrides: Partial<ComponentProps<typeof DesktopTerrainSidebar>> = {},
): ComponentProps<typeof DesktopTerrainSidebar> {
  return {
    route: { kind: 'static', path: '/general' },
    collapsed: false,
    onCollapsedChange: vi.fn(),
    navigate: vi.fn(),
    ...overrides,
  }
}

afterEach(() => {
  cleanup()
  lgViewportState.current = false
  vi.unstubAllEnvs()
})

const crossSignalsRoute: AppRoute = {
  kind: 'scoped-terrain',
  scope: { type: 'cross' },
  page: 'signals',
}

describe('DesktopTerrainSidebar', () => {
  it('renders one establishment destination list for a single-establishment manager', () => {
    renderSidebar(
      <DesktopTerrainSidebar
        {...sidebarProps({
          bootstrap: bootstrap([membership({ role: 'manager' })]),
        })}
      />,
    )

    const sidebar = screen.getByLabelText('Navigation principale')
    expect(within(sidebar).getByText('Spore')).toBeTruthy()
    expect(within(sidebar).queryByText('Spore Analytics')).toBeNull()
    expect(within(sidebar).queryByText('Cross-établissement')).toBeNull()
    expect(within(sidebar).getByText('Spore Paris')).toBeTruthy()
    expect(within(sidebar).getByRole('link', { name: 'Dashboard' })).toBeTruthy()
    expect(within(sidebar).getByRole('link', { name: 'Observations' })).toBeTruthy()
    expect(within(sidebar).getByRole('link', { name: 'Nouvelle observation' })).toBeTruthy()
  })

  it('navigates to the establishment observations feed for a single-establishment manager', () => {
    const navigate = vi.fn()
    renderSidebar(
      <DesktopTerrainSidebar
        {...sidebarProps({
          bootstrap: bootstrap([membership({ role: 'manager' })]),
          navigate,
        })}
      />,
    )

    fireEvent.click(screen.getByRole('link', { name: 'Observations' }))
    expect(navigate).toHaveBeenCalledWith('/e/est-1/signals')
  })

  it('navigates to the Cross observations feed when Cross scope is real', () => {
    const navigate = vi.fn()
    renderSidebar(
      <DesktopTerrainSidebar
        {...sidebarProps({
          route: crossSignalsRoute,
          bootstrap: bootstrap([
            membership({
              role: 'manager',
              establishment_id: 'est-1',
              establishment_name: 'Spore Paris',
            }),
            membership({
              role: 'manager',
              establishment_id: 'est-2',
              establishment_name: 'Spore Lyon',
            }),
          ]),
          navigate,
        })}
      />,
    )

    const sidebar = screen.getByLabelText('Navigation principale')
    expect(within(sidebar).getAllByText('Cross-établissement').length).toBeGreaterThan(0)
    fireEvent.click(screen.getByRole('link', { name: 'Observations' }))
    expect(navigate).toHaveBeenCalledWith('/cross/signals')
  })

  it('hides Cross for Staff-only users', () => {
    renderSidebar(
      <DesktopTerrainSidebar
        {...sidebarProps({
          route: {
            kind: 'scoped-terrain',
            scope: { type: 'establishment', establishmentId: 'est-1' },
            page: 'signals',
          },
          bootstrap: bootstrap([membership({ role: 'staff' })]),
        })}
      />,
    )

    const sidebar = screen.getByLabelText('Navigation principale')
    expect(within(sidebar).queryByText('Cross-établissement')).toBeNull()
    expect(within(sidebar).queryByRole('link', { name: 'Dashboard' })).toBeNull()
    expect(within(sidebar).getByRole('link', { name: 'Observations' })).toBeTruthy()
  })

  it('shows French role labels in the footer context line', () => {
    renderSidebar(
      <DesktopTerrainSidebar
        {...sidebarProps({
          bootstrap: bootstrap([membership({ role: 'owner' })]),
        })}
      />,
    )

    const sidebar = screen.getByLabelText('Navigation principale')
    expect(within(sidebar).getByText('Propriétaire · Spore Paris')).toBeTruthy()
    expect(within(sidebar).queryByText(/Owner/)).toBeNull()
  })

  it('names the Cross footer without the session establishment', () => {
    renderSidebar(
      <DesktopTerrainSidebar
        {...sidebarProps({
          route: crossSignalsRoute,
          bootstrap: bootstrap([
            membership({ role: 'owner', establishment_id: 'est-1', establishment_name: 'Spore Paris' }),
            membership({ role: 'owner', establishment_id: 'est-2', establishment_name: 'Spore Lyon' }),
          ]),
        })}
      />,
    )

    const sidebar = screen.getByLabelText('Navigation principale')
    expect(within(sidebar).getAllByText('Cross-établissement').length).toBeGreaterThan(0)
    expect(within(sidebar).queryByText(/Spore Paris/)).toBeNull()
  })

  it('does not offer client establishment creation', () => {
    renderSidebar(
      <DesktopTerrainSidebar
        {...sidebarProps({
          bootstrap: bootstrap([membership({ role: 'owner' })], {
            can_manage_organization: true,
            platform_operator_active: false,
          }),
        })}
      />,
    )

    expect(screen.queryByRole('button', { name: /Ajouter un établissement/i })).toBeNull()
  })

  it('switches scope to the same hub and does not copy a query', () => {
    const navigate = vi.fn()
    const paris = membership({
      role: 'manager',
      establishment_id: 'est-1',
      establishment_name: 'Spore Paris',
      chat_available: true,
    })
    const lyon = membership({
      role: 'manager',
      establishment_id: 'est-2',
      establishment_name: 'Spore Lyon',
      chat_available: false,
    })
    renderSidebar(
      <DesktopTerrainSidebar
        {...sidebarProps({
          route: crossSignalsRoute,
          bootstrap: bootstrap([paris, lyon], { chat_available: false }, null),
          navigate,
        })}
      />,
    )

    const sidebar = screen.getByLabelText('Navigation principale')
    expect(within(sidebar).queryByRole('link', { name: 'Chat' })).toBeNull()
    fireEvent.click(within(sidebar).getByRole('button', { name: 'Cross-établissement' }))
    fireEvent.change(screen.getByRole('textbox', { name: 'Rechercher un scope' }), {
      target: { value: 'Lyon' },
    })
    expect(screen.getByRole('option', { name: 'Spore Lyon' })).toBeTruthy()
    expect(screen.queryByRole('option', { name: 'Spore Paris' })).toBeNull()
    fireEvent.keyDown(screen.getByRole('textbox', { name: 'Rechercher un scope' }), {
      key: 'Enter',
    })
    expect(navigate).toHaveBeenCalledWith('/e/est-2/signals')
    expect(navigate.mock.calls[0]?.[0]).not.toContain('?')
  })

  it('marks Chat active on a conversation and Général active on the library', () => {
    const { unmount } = renderSidebar(
      <DesktopTerrainSidebar
        {...sidebarProps({
          route: { kind: 'chat-conversation-detail', conversationId: 'conversation-1' },
          bootstrap: bootstrap([membership({ role: 'manager', chat_available: true })]),
        })}
      />,
    )
    expect(screen.getByRole('link', { name: 'Chat' }).getAttribute('aria-current')).toBe('page')
    unmount()

    renderSidebar(
      <DesktopTerrainSidebar
        {...sidebarProps({
          route: { kind: 'static', path: '/action-plans' },
          bootstrap: bootstrap([membership({ role: 'manager' })]),
        })}
      />,
    )
    expect(screen.getByRole('link', { name: 'Général' }).getAttribute('aria-current')).toBe('page')
  })

  it('keeps destinations reachable when the sidebar is collapsed', () => {
    lgViewportState.current = true
    renderSidebar(
      <DesktopTerrainSidebar
        {...sidebarProps({
          collapsed: true,
          bootstrap: bootstrap([membership({ role: 'manager' })]),
          onSignOut: vi.fn(),
        })}
      />,
    )

    const sidebar = screen.getByLabelText('Navigation principale')
    expect(sidebar.getAttribute('data-collapsed')).toBe('true')
    expect(within(sidebar).getByRole('link', { name: 'Observations' })).toBeTruthy()
    expect(within(sidebar).getByRole('button', { name: 'Scope : Spore Paris' })).toBeTruthy()
    expect(within(sidebar).getByLabelText('Marie Renaud')).toBeTruthy()
    expect(within(sidebar).getByRole('button', { name: 'Déconnexion' })).toBeTruthy()
    expect(within(sidebar).getByRole('button', { name: 'Développer la navigation' })).toBeTruthy()
  })

  it('signs out from the footer on desktop web', () => {
    lgViewportState.current = true
    const onSignOut = vi.fn()
    renderSidebar(
      <DesktopTerrainSidebar
        {...sidebarProps({
          bootstrap: bootstrap([membership({ role: 'manager' })]),
          onSignOut,
        })}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Déconnexion' }))
    expect(onSignOut).toHaveBeenCalledTimes(1)
  })

  it('disables footer sign-out while logout is in progress', () => {
    lgViewportState.current = true
    renderSidebar(
      <DesktopTerrainSidebar
        {...sidebarProps({
          bootstrap: bootstrap([membership({ role: 'manager' })]),
          isLoggingOut: true,
          onSignOut: vi.fn(),
        })}
      />,
    )

    expect(
      (screen.getByRole('button', { name: 'Déconnexion...' }) as HTMLButtonElement).disabled,
    ).toBe(true)
  })

  it('hides footer sign-out on native even at a large viewport', () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    lgViewportState.current = true
    renderSidebar(
      <DesktopTerrainSidebar
        {...sidebarProps({
          bootstrap: bootstrap([membership({ role: 'manager' })]),
          onSignOut: vi.fn(),
        })}
      />,
    )

    expect(screen.queryByRole('button', { name: /Déconnexion/ })).toBeNull()
  })
})
