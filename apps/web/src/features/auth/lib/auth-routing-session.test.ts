import { describe, expect, it } from 'vitest'

import { resolveAuthRoutingSession } from '@/features/auth/lib/auth-routing-session'
import type { BootstrapResponse, Membership } from '@/features/auth/types'

function membership(id: string, establishmentId: string): Membership {
  return {
    id,
    establishment_id: establishmentId,
    establishment_name: `Establishment ${establishmentId}`,
    organization_id: 'org-1',
    organization_name: 'Org',
    role: 'staff',
    status: 'active',
    chat_available: true,
    scopes: [],
    scope_summary: { business_unit_count: 0 },
  }
}

function bootstrap(activeEstablishmentId: string | null): BootstrapResponse {
  const memberships = [membership('member-1', 'est-1'), membership('member-2', 'est-2')]
  const active =
    activeEstablishmentId === null
      ? null
      : (memberships.find((item) => item.establishment_id === activeEstablishmentId) ?? null)

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
      can_manage_runtime_config: false,
      can_view_team: false,
      can_manage_organization: false,
      platform_operator_active: false,
    },
  }
}

describe('resolveAuthRoutingSession', () => {
  it('prefers the Query cache over the AuthProvider fallback', () => {
    const cached = bootstrap('est-2')
    const fallback = bootstrap(null)

    expect(resolveAuthRoutingSession(cached, fallback)).toEqual({
      bootstrap: cached,
      hasOperationalAccess: true,
      memberships: cached.memberships,
      sessionEstablishmentId: 'est-2',
    })
  })

  it('falls back to AuthProvider when the cache is empty', () => {
    const fallback = bootstrap('est-1')

    expect(resolveAuthRoutingSession(undefined, fallback)).toEqual({
      bootstrap: fallback,
      hasOperationalAccess: true,
      memberships: fallback.memberships,
      sessionEstablishmentId: 'est-1',
    })
  })

  it('reports no operational access when neither cache nor fallback has an active membership', () => {
    const fallback = bootstrap(null)

    expect(resolveAuthRoutingSession(undefined, fallback)).toEqual({
      bootstrap: fallback,
      hasOperationalAccess: false,
      memberships: fallback.memberships,
      sessionEstablishmentId: null,
    })
  })
})
