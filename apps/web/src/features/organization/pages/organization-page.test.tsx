// @vitest-environment jsdom

import { createElement, type ReactNode } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { OrganizationPage } from './organization-page'
import type { BootstrapResponse, Membership } from '@/features/auth/types'
import type { PendingOnboardingMembership } from '@/features/auth/lib/pending-onboarding'

const { authState } = vi.hoisted(() => ({
  authState: {
    current: {
      activeMembership: null as Membership | null,
      bootstrap: null as BootstrapResponse | null,
      isBootstrapping: false,
      isReady: true,
    },
  },
}))

vi.mock('@/app/auth-provider', () => ({
  useAuth: () => authState.current,
}))

vi.mock('@/lib/lg-viewport', () => ({
  useLgViewport: () => true,
}))

vi.mock('../hooks', () => ({
  useOrganizationOverviewQuery: () => ({
    data: {
      name: 'Org',
      active_establishment_count: 0,
      draft_establishment_count: 1,
    },
    isLoading: false,
  }),
  useOrganizationEstablishmentsQuery: () => ({ data: { results: [] } }),
  useOrganizationMembersQuery: () => ({ data: { results: [] }, isLoading: false }),
  useOrganizationMemberFilterOptionsQuery: () => ({ data: undefined }),
  useOrganizationOwnersQuery: () => ({ data: { results: [] }, isLoading: false }),
  useInviteOrganizationOwnerMutation: () => ({
    isPending: false,
    mutateAsync: vi.fn(),
  }),
  useCreateOrganizationEstablishmentMutation: () => ({
    isPending: false,
    mutateAsync: vi.fn(),
  }),
}))

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

function pendingDraft(): PendingOnboardingMembership {
  return {
    id: 'pending-1',
    establishment_id: 'draft-1',
    establishment_name: 'Hôtel Draft',
    establishment_status: 'draft',
    organization_id: 'org-1',
    organization_name: 'Spore',
    role: 'owner',
    onboarding_session_id: 'session-1',
    can_continue_onboarding: true,
  }
}

function bootstrap(options: {
  memberships?: Membership[]
  activeMembership?: Membership | null
  pending?: PendingOnboardingMembership[]
}): BootstrapResponse {
  const memberships = options.memberships ?? []
  return {
    authenticated: true,
    user: {
      id: 'user-1',
      username: 'owner',
      email: 'owner@example.com',
      identity_type: 'human',
      first_name: 'Owner',
      last_name: 'One',
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
    active_membership: options.activeMembership ?? memberships[0] ?? null,
    pending_onboarding_memberships: options.pending ?? [],
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
  }
}

function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })

  function Wrapper({ children }: { children: ReactNode }) {
    return createElement(QueryClientProvider, { client }, children)
  }

  return render(createElement(OrganizationPage, { onNavigate: vi.fn() }), {
    wrapper: Wrapper,
  })
}

afterEach(() => {
  cleanup()
})

describe('OrganizationPage create establishment entry', () => {
  it('keeps the create CTA when there is no active membership', () => {
    const current = bootstrap({
      memberships: [],
      activeMembership: null,
      pending: [pendingDraft()],
    })
    authState.current = {
      activeMembership: null,
      bootstrap: current,
      isBootstrapping: false,
      isReady: true,
    }

    renderPage()

    expect(screen.getByRole('button', { name: /Ajouter un établissement/i })).toBeTruthy()
  })

  it('hides the create CTA when an active membership exists', () => {
    const active = membership()
    const current = bootstrap({
      memberships: [active],
      activeMembership: active,
    })
    authState.current = {
      activeMembership: active,
      bootstrap: current,
      isBootstrapping: false,
      isReady: true,
    }

    renderPage()

    expect(screen.queryByRole('button', { name: /Ajouter un établissement/i })).toBeNull()
  })
})
