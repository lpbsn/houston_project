// @vitest-environment jsdom

import { createElement, type ReactNode } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { DesktopTerrainSidebar } from '@/components/layout/desktop-terrain-sidebar'
import type { BootstrapResponse, Membership } from '@/features/auth/types'

const createEstablishment = vi.fn()

vi.mock('@/features/auth/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/features/auth/api')>()
  return {
    ...actual,
    createEstablishment: (...args: unknown[]) => createEstablishment(...args),
  }
})

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

function bootstrap(
  memberships: Membership[],
  hints: Partial<BootstrapResponse['permission_hints']> = {},
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

afterEach(() => {
  cleanup()
  createEstablishment.mockReset()
})

describe('DesktopTerrainSidebar', () => {
  it('renders the establishment section for a single-establishment manager without Cross', () => {
    renderSidebar(
      <DesktopTerrainSidebar
        activePath="/analytics"
        bootstrap={bootstrap([membership({ role: 'manager' })])}
        navigate={vi.fn()}
        showChat={true}
      />,
    )

    const sidebar = screen.getByLabelText('Navigation principale')
    expect(within(sidebar).getByText('Spore Analytics')).toBeTruthy()
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
        activePath="/analytics"
        bootstrap={bootstrap([membership({ role: 'manager' })])}
        navigate={navigate}
        showChat={false}
      />,
    )

    fireEvent.click(screen.getByRole('link', { name: 'Observations' }))
    expect(navigate).toHaveBeenCalledWith('/e/est-1/signals')
  })

  it('navigates to the Cross observations feed when Cross scope is real', () => {
    const navigate = vi.fn()
    renderSidebar(
      <DesktopTerrainSidebar
        activePath="/cross"
        bootstrap={bootstrap([
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
        ])}
        navigate={navigate}
        showChat={false}
      />,
    )

    const sidebar = screen.getByLabelText('Navigation principale')
    expect(within(sidebar).getByText('Cross-établissement')).toBeTruthy()
    fireEvent.click(screen.getByRole('link', { name: 'Observations' }))
    expect(navigate).toHaveBeenCalledWith('/cross/signals')
  })

  it('hides Cross for Staff-only users', () => {
    renderSidebar(
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
    renderSidebar(
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

  it('shows create establishment above scoped sections for a single-establishment owner without Cross', () => {
    renderSidebar(
      <DesktopTerrainSidebar
        activePath="/analytics"
        bootstrap={bootstrap([membership({ role: 'owner' })], {
          can_create_establishment: true,
          can_manage_organization: true,
        })}
        navigate={vi.fn()}
        showChat={false}
      />,
    )

    const sidebar = screen.getByLabelText('Navigation principale')
    expect(within(sidebar).getByRole('button', { name: /Ajouter un établissement/i })).toBeTruthy()
    expect(within(sidebar).queryByText('Cross-établissement')).toBeNull()
  })

  it('keeps create establishment when Cross is visible', () => {
    renderSidebar(
      <DesktopTerrainSidebar
        activePath="/cross"
        bootstrap={bootstrap(
          [
            membership({
              role: 'owner',
              establishment_id: 'est-1',
              establishment_name: 'Spore Paris',
            }),
            membership({
              role: 'owner',
              id: 'membership-owner-2',
              establishment_id: 'est-2',
              establishment_name: 'Spore Lyon',
            }),
          ],
          { can_create_establishment: true, can_manage_organization: true },
        )}
        navigate={vi.fn()}
        showChat={false}
      />,
    )

    const sidebar = screen.getByLabelText('Navigation principale')
    expect(within(sidebar).getByRole('button', { name: /Ajouter un établissement/i })).toBeTruthy()
    expect(within(sidebar).getByText('Cross-établissement')).toBeTruthy()
  })

  it('hides create establishment for staff', () => {
    renderSidebar(
      <DesktopTerrainSidebar
        activePath="/e/est-1/signals"
        bootstrap={bootstrap([membership({ role: 'staff' })])}
        navigate={vi.fn()}
        showChat={true}
      />,
    )

    expect(screen.queryByRole('button', { name: /Ajouter un établissement/i })).toBeNull()
  })

  it('creates an establishment from the sidebar and navigates to onboarding', async () => {
    const navigate = vi.fn()
    createEstablishment.mockResolvedValueOnce({
      establishment_id: 'est-new',
      organization_id: 'org-1',
      name: null,
      status: 'draft',
      onboarding_session_id: 'session-1',
    })

    renderSidebar(
      <DesktopTerrainSidebar
        activePath="/analytics"
        bootstrap={bootstrap([membership({ role: 'owner' })], {
          can_create_establishment: true,
          can_manage_organization: true,
        })}
        navigate={navigate}
        showChat={false}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: /Ajouter un établissement/i }))

    expect(screen.queryByPlaceholderText(/Nom de l’établissement/i)).toBeNull()
    await waitFor(() => {
      expect(createEstablishment).toHaveBeenCalledWith({})
    })
    await waitFor(() => {
      expect(navigate).toHaveBeenCalledWith(
        '/onboarding?establishmentId=est-new&sessionId=session-1',
      )
    })
  })
})
