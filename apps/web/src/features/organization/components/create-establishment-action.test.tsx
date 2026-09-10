// @vitest-environment jsdom

import { createElement, type ReactNode } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { CreateEstablishmentAction } from './create-establishment-action'
import type { BootstrapResponse, Membership } from '@/features/auth/types'

const createEstablishment = vi.fn()

vi.mock('@/features/auth/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/features/auth/api')>()
  return {
    ...actual,
    createEstablishment: (...args: unknown[]) => createEstablishment(...args),
  }
})

function membership(overrides: Partial<Membership> = {}): Membership {
  return {
    id: overrides.id ?? 'membership-1',
    establishment_id: overrides.establishment_id ?? 'est-1',
    establishment_name: overrides.establishment_name ?? 'Spore Paris',
    organization_id: overrides.organization_id ?? 'org-1',
    organization_name: overrides.organization_name ?? 'Spore',
    role: overrides.role ?? 'owner',
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
      can_manage_organization: true,
      can_create_establishment: true,
      ...hints,
    },
  }
}

function renderAction(
  ui: ReactNode,
  queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  }),
) {
  return render(
    createElement(QueryClientProvider, { client: queryClient }, ui),
  )
}

afterEach(() => {
  cleanup()
  createEstablishment.mockReset()
})

describe('CreateEstablishmentAction', () => {
  it('hides the trigger when the bootstrap hint is false', () => {
    renderAction(
      createElement(CreateEstablishmentAction, {
        bootstrap: bootstrap([membership()], { can_create_establishment: false }),
        navigate: vi.fn(),
        triggerVariant: 'organization',
      }),
    )

    expect(screen.queryByRole('button', { name: /Ajouter un établissement/i })).toBeNull()
  })

  it('provisions without a name sheet then navigates to onboarding', async () => {
    const navigate = vi.fn()
    createEstablishment.mockResolvedValueOnce({
      establishment_id: 'est-new',
      organization_id: 'org-1',
      name: null,
      status: 'draft',
      onboarding_session_id: 'session-1',
    })

    renderAction(
      createElement(CreateEstablishmentAction, {
        bootstrap: bootstrap([membership()]),
        navigate,
        triggerVariant: 'organization',
      }),
    )

    fireEvent.click(screen.getByRole('button', { name: /Ajouter un établissement/i }))

    expect(screen.queryByRole('dialog')).toBeNull()
    expect(screen.queryByPlaceholderText(/Nom de l’établissement/i)).toBeNull()
    await waitFor(() => {
      expect(createEstablishment).toHaveBeenCalledWith({})
    })
    await waitFor(() => {
      expect(navigate).toHaveBeenCalledWith('/onboarding?establishmentId=est-new&sessionId=session-1')
    })
  })

  it('shows an inline error when creation fails', async () => {
    createEstablishment.mockRejectedValueOnce(new Error('Création refusée.'))

    renderAction(
      createElement(CreateEstablishmentAction, {
        bootstrap: bootstrap([membership()]),
        navigate: vi.fn(),
        triggerVariant: 'organization',
      }),
    )

    fireEvent.click(screen.getByRole('button', { name: /Ajouter un établissement/i }))

    expect(await screen.findByText('Création refusée.')).toBeTruthy()
    expect(screen.queryByRole('dialog')).toBeNull()
  })
})
