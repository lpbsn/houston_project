// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { DesktopTerrainSidebar } from '@/components/layout/desktop-terrain-sidebar'
import type { BootstrapResponse, Membership } from '@/features/auth/types'

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
    active_membership: memberships[0] ?? null,
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

afterEach(() => {
  cleanup()
})

describe('DesktopTerrainSidebar', () => {
  it('renders scoped Cross and establishment sections for managers', () => {
    render(
      <DesktopTerrainSidebar
        activePath="/cross"
        bootstrap={bootstrap([membership({ role: 'manager' })])}
        navigate={vi.fn()}
        showChat={true}
      />,
    )

    const sidebar = screen.getByLabelText('Navigation principale')
    expect(within(sidebar).getByText('Spore Analytics')).toBeTruthy()
    expect(within(sidebar).getByText('Cross-établissement')).toBeTruthy()
    expect(within(sidebar).getByRole('link', { name: 'Dashboard' })).toBeTruthy()
    expect(within(sidebar).getByText('Spore Paris')).toBeTruthy()
  })

  it('navigates to the Cross observations feed', () => {
    const navigate = vi.fn()
    render(
      <DesktopTerrainSidebar
        activePath="/cross"
        bootstrap={bootstrap([membership({ role: 'manager' })] )}
        navigate={navigate}
        showChat={false}
      />,
    )

    fireEvent.click(screen.getByRole('link', { name: 'Observations' }))
    expect(navigate).toHaveBeenCalledWith('/cross/signals')
  })

  it('hides Cross for Staff-only users', () => {
    render(
      <DesktopTerrainSidebar
        activePath="/e/est-1/signals"
        bootstrap={bootstrap([membership({ role: 'staff' })])}
        navigate={vi.fn()}
        showChat={true}
      />,
    )

    const sidebar = screen.getByLabelText('Navigation principale')
    expect(within(sidebar).queryByText('Cross-établissement')).toBeNull()
    expect(within(sidebar).queryByRole('link', { name: 'Dashboard' })).toBeNull()
    expect(within(sidebar).getByRole('link', { name: 'Observations' })).toBeTruthy()
  })

  it('shows French role labels in the footer context line', () => {
    render(
      <DesktopTerrainSidebar
        activePath="/cross"
        bootstrap={bootstrap([membership({ role: 'owner' })])}
        navigate={vi.fn()}
        showChat={false}
      />,
    )

    const sidebar = screen.getByLabelText('Navigation principale')
    expect(within(sidebar).getByText('Propriétaire · Spore Paris')).toBeTruthy()
    expect(within(sidebar).queryByText(/Owner/)).toBeNull()
  })
})
