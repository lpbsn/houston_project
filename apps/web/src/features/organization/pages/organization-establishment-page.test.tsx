// @vitest-environment jsdom

import { createElement, type ReactNode } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { OrganizationEstablishmentPage } from './organization-establishment-page'
import type { BootstrapResponse, Membership } from '@/features/auth/types'

const EST_ID = '11111111-1111-4111-8111-111111111111'

const { authState, lgState, switchEstablishment } = vi.hoisted(() => ({
  authState: {
    current: {
      activeMembership: null as Membership | null,
      bootstrap: null as BootstrapResponse | null,
      isBootstrapping: false,
      isReady: true,
    },
  },
  lgState: { current: true },
  switchEstablishment: vi.fn(),
}))

vi.mock('@/app/auth-provider', () => ({
  useAuth: () => authState.current,
}))

vi.mock('@/lib/lg-viewport', () => ({
  useLgViewport: () => lgState.current,
}))

vi.mock('@/lib/runtime', () => ({
  getAppRuntime: () => 'web',
}))

vi.mock('@/features/auth/api', () => ({
  switchEstablishment: (...args: unknown[]) => switchEstablishment(...args),
}))

vi.mock('../hooks', () => ({
  useEstablishmentAdminOverviewQuery: () => ({
    data: {
      id: EST_ID,
      name: 'Spore Paris',
      organization_name: 'Spore',
      status: 'active',
      directors: [],
      active_member_count: 1,
      business_unit_count: 1,
      metrics: {
        signals_open: 0,
        signals_in_progress: 0,
        action_plans_in_progress: 0,
        action_plans_scheduled: 0,
        observations_weekly_average: 0,
      },
      operational_config: {
        status: 'configured',
        active_business_unit_count: 1,
        active_activity_subject_count: 1,
        active_business_units_without_subjects_count: 0,
      },
    },
    isLoading: false,
    isError: false,
  }),
  useEstablishmentAdminMembershipsQuery: () => ({
    data: { results: [] },
    isLoading: false,
  }),
  useEstablishmentAdminMemberFilterOptionsQuery: () => ({ data: undefined }),
  useInviteEstablishmentAdminMembershipMutation: () => ({ mutateAsync: vi.fn() }),
  useUpdateEstablishmentAdminMembershipMutation: () => ({ mutateAsync: vi.fn() }),
  useDeactivateEstablishmentAdminMembershipMutation: () => ({ mutateAsync: vi.fn() }),
  useActivateEstablishmentAdminMembershipMutation: () => ({ mutateAsync: vi.fn() }),
}))

function membership(overrides: Partial<Membership> = {}): Membership {
  return {
    id: overrides.id ?? 'membership-1',
    establishment_id: overrides.establishment_id ?? EST_ID,
    establishment_name: overrides.establishment_name ?? 'Spore Paris',
    organization_id: overrides.organization_id ?? 'org-1',
    organization_name: overrides.organization_name ?? 'Spore',
    role: overrides.role ?? 'director',
    status: overrides.status ?? 'active',
    scopes: [],
    scope_summary: { business_unit_count: 0 },
  }
}

function bootstrap(active: Membership): BootstrapResponse {
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
    memberships: [active],
    active_membership: active,
    pending_onboarding_memberships: [],
    permission_hints: {
      chat_available: false,
      can_create_action_plan: false,
      can_create_catalog_action_plan: false,
      can_view_action_plan_catalog: false,
      can_invite: true,
      can_manage_runtime_config: true,
      can_view_team: true,
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
  lgState.current = true
  switchEstablishment.mockReset()
})

describe('OrganizationEstablishmentPage operational config CTA', () => {
  it('navigates to the scoped path on desktop without switching locally', () => {
    const director = membership()
    authState.current = {
      activeMembership: director,
      bootstrap: bootstrap(director),
      isBootstrapping: false,
      isReady: true,
    }
    const onNavigate = vi.fn()

    render(
      wrap(
        createElement(OrganizationEstablishmentPage, {
          establishmentId: EST_ID,
          onNavigate,
        }),
      ),
    )

    fireEvent.click(screen.getByRole('button', { name: 'Configuration opérationnelle' }))
    expect(onNavigate).toHaveBeenCalledWith(`/e/${EST_ID}/operational-config`)
    expect(switchEstablishment).not.toHaveBeenCalled()
  })

  it('hides the CTA off desktop', () => {
    lgState.current = false
    const director = membership()
    authState.current = {
      activeMembership: director,
      bootstrap: bootstrap(director),
      isBootstrapping: false,
      isReady: true,
    }

    render(
      wrap(
        createElement(OrganizationEstablishmentPage, {
          establishmentId: EST_ID,
          onNavigate: vi.fn(),
        }),
      ),
    )

    expect(screen.queryByRole('button', { name: 'Configuration opérationnelle' })).toBeNull()
  })
})
