// @vitest-environment jsdom

import { createElement, type ReactNode } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { BusinessUnitTreeItem } from '@/features/establishment-config/api'
import type { BootstrapResponse, Membership } from '@/features/auth/types'

import { OperationalConfigPage } from './operational-config-page'

const { authState, treeState } = vi.hoisted(() => ({
  authState: {
    current: {
      activeMembership: null as Membership | null,
      bootstrap: null as BootstrapResponse | null,
    },
  },
  treeState: {
    fetchCount: 0,
    businessUnits: [] as BusinessUnitTreeItem[],
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
        business_units: treeState.businessUnits,
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
  useUpdateRuntimeBusinessUnit: () => ({ isPending: false, mutateAsync: vi.fn() }),
  useDeactivateRuntimeBusinessUnit: () => ({ isPending: false, mutateAsync: vi.fn() }),
  useReactivateRuntimeBusinessUnit: () => ({ isPending: false, mutateAsync: vi.fn() }),
  useCreateRuntimeActivitySubject: () => ({ isPending: false, mutateAsync: vi.fn() }),
  useDeactivateRuntimeActivitySubject: () => ({ isPending: false, mutateAsync: vi.fn() }),
  useReactivateRuntimeActivitySubject: () => ({ isPending: false, mutateAsync: vi.fn() }),
  useActivityDescription: () => ({
    data: { description: 'Description déjà enregistrée pour cet établissement.' },
    isPending: false,
    error: null,
    refetch: vi.fn(),
  }),
  useUpdateActivityDescription: () => ({
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
    chat_available: overrides.chat_available ?? true,
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
      platform_operator_active: false,
    },
  }
}

function wrap(node: ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return createElement(QueryClientProvider, { client }, node)
}

function pole(overrides: Partial<BusinessUnitTreeItem> = {}): BusinessUnitTreeItem {
  return {
    id: 'bu-1',
    specific_name: 'Hôtel',
    instance_description: 'Description du pôle.',
    active: true,
    generic: {
      key: 'hotel',
      label: 'Hôtel',
      description: '',
      unit_type: 'dedicated',
    },
    activity_subjects: [
      {
        id: 'subject-1',
        label: 'Accueil',
        description: '',
        source: 'manual',
        active: true,
        is_generic: true,
      },
    ],
    ...overrides,
  }
}

afterEach(() => {
  cleanup()
  treeState.fetchCount = 0
  treeState.businessUnits = []
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

    expect(screen.getByText('Description de l’établissement')).toBeTruthy()
    expect(screen.getByText('Ajouter un pôle')).toBeTruthy()
    expect(screen.queryByText('Retour')).toBeNull()
    expect(treeState.fetchCount).toBe(1)
  })

  it('keeps an unsaved pole draft when its subject list changes', () => {
    const director = membership({ role: 'director' })
    const lyon = membership({
      id: 'membership-2',
      establishment_id: 'est-2',
      establishment_name: 'Lyon',
      role: 'director',
    })
    authState.current = {
      activeMembership: director,
      bootstrap: bootstrap([director, lyon], director),
    }
    treeState.businessUnits = [pole()]

    const view = render(wrap(createElement(OperationalConfigPage, { establishmentId: 'est-1' })))
    fireEvent.change(screen.getByLabelText('Nom d’instance'), { target: { value: 'Hôtel patio' } })
    fireEvent.change(screen.getByLabelText('Description d’instance'), {
      target: { value: 'Brouillon local du pôle.' },
    })

    treeState.businessUnits = [
      pole({
        activity_subjects: [
          {
            id: 'subject-1',
            label: 'Accueil',
            description: '',
            source: 'manual',
            active: true,
            is_generic: true,
          },
          {
            id: 'subject-2',
            label: 'Réservation',
            description: '',
            source: 'manual',
            active: true,
            is_generic: false,
          },
        ],
      }),
    ]
    view.rerender(wrap(createElement(OperationalConfigPage, { establishmentId: 'est-1' })))

    expect((screen.getByLabelText('Nom d’instance') as HTMLInputElement).value).toBe('Hôtel patio')
    expect((screen.getByLabelText('Description d’instance') as HTMLTextAreaElement).value).toBe(
      'Brouillon local du pôle.',
    )
    expect(screen.getByText('Réservation')).toBeTruthy()

    authState.current = {
      activeMembership: lyon,
      bootstrap: bootstrap([director, lyon], lyon),
    }
    treeState.businessUnits = [
      pole({
        id: 'bu-lyon',
        specific_name: 'Cuisine',
        instance_description: 'Pôle de Lyon.',
      }),
    ]
    view.rerender(wrap(createElement(OperationalConfigPage, { establishmentId: 'est-2' })))

    expect((screen.getByLabelText('Nom d’instance') as HTMLInputElement).value).toBe('Cuisine')
    expect((screen.getByLabelText('Description d’instance') as HTMLTextAreaElement).value).toBe(
      'Pôle de Lyon.',
    )
  })
})
