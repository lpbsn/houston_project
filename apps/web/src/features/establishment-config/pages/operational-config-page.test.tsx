// @vitest-environment jsdom

import { createElement, type ReactNode } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { OperationalConfigPage } from './operational-config-page'
import type { BootstrapResponse, Membership } from '@/features/auth/types'

const { authState, treeState } = vi.hoisted(() => ({
  authState: {
    current: {
      activeMembership: null as Membership | null,
      bootstrap: null as BootstrapResponse | null,
    },
  },
  treeState: {
    fetchCount: 0,
  },
}))

vi.mock('@/app/auth-provider', () => ({
  useAuth: () => authState.current,
}))

vi.mock('@/features/establishment-config/hooks', () => ({
  useOperationalConfigTree: (establishmentId: string) => {
    treeState.fetchCount += 1
    return {
      data: {
        establishment_name: 'Spore Paris',
        establishment_id: establishmentId,
        business_units: [],
      },
      isPending: false,
      error: null,
      refetch: vi.fn(),
    }
  },
  useCreateRuntimeBusinessUnit: () => ({
    isPending: false,
    mutateAsync: vi.fn(),
  }),
}))

vi.mock('@/features/onboarding/components/business-unit-autocomplete', () => ({
  BusinessUnitAutocomplete: () => createElement('div', null, 'autocomplete'),
}))

function membership(overrides: Partial<Membership> = {}): Membership {
  return {
    id: overrides.id ?? 'membership-1',
    establishment_id: overrides.establishment_id ?? 'est-1',
    establishment_name: overrides.establishment_name ?? 'Spore Paris',
    organization_id: overrides.organization_id ?? 'org-1',
    organization_name: overrides.organization_name ?? 'Spore',
    role: overrides.role ?? 'director',
    status: overrides.status ?? 'active',
    scopes: [],
    scope_summary: { business_unit_count: 0 },
  }
}

function bootstrap(memberships: Membership[], active: Membership | null): BootstrapResponse {
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
    active_membership: active,
    pending_onboarding_memberships: [],
    permission_hints: {
      chat_available: false,
      can_create_action_plan: false,
      can_create_catalog_action_plan: false,
      can_view_action_plan_catalog: false,
      can_invite: false,
      can_manage_runtime_config: true,
      can_view_team: false,
      can_manage_organization: false,
      can_create_establishment: false,
    },
  }
}

function wrap(node: ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return createElement(QueryClientProvider, { client }, node)
}

afterEach(() => {
  cleanup()
  treeState.fetchCount = 0
})

describe('OperationalConfigPage', () => {
  it('denies staff even when the session establishment matches', () => {
    const staff = membership({ role: 'staff' })
    authState.current = {
      activeMembership: staff,
      bootstrap: bootstrap([staff], staff),
    }

    render(wrap(createElement(OperationalConfigPage, { establishmentId: 'est-1' })))

    expect(screen.getByText('Accès refusé')).toBeTruthy()
    expect(screen.queryByText('Retour')).toBeNull()
    expect(treeState.fetchCount).toBe(0)
  })

  it('does not fetch while the session still points at another establishment', () => {
    const here = membership({ establishment_id: 'est-1', role: 'director' })
    const there = membership({
      id: 'membership-2',
      establishment_id: 'est-2',
      establishment_name: 'Lyon',
      role: 'director',
    })
    authState.current = {
      activeMembership: there,
      bootstrap: bootstrap([here, there], there),
    }

    render(wrap(createElement(OperationalConfigPage, { establishmentId: 'est-1' })))

    expect(screen.getByText('Chargement de la configuration opérationnelle…')).toBeTruthy()
    expect(treeState.fetchCount).toBe(0)
  })

  it('loads the editor when the route establishment is the session', () => {
    const director = membership({ role: 'director' })
    authState.current = {
      activeMembership: director,
      bootstrap: bootstrap([director], director),
    }

    render(wrap(createElement(OperationalConfigPage, { establishmentId: 'est-1' })))

    expect(screen.getByText('Ajouter un pôle')).toBeTruthy()
    expect(screen.queryByText('Retour')).toBeNull()
    expect(treeState.fetchCount).toBe(1)
  })
})
