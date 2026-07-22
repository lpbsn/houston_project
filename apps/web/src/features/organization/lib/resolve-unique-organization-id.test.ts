import { describe, expect, it } from 'vitest'

import type { BootstrapResponse } from '@/features/auth/types'

import { resolveUniqueOrganizationId } from './resolve-unique-organization-id'

function bootstrapFixture(
  partial: Partial<BootstrapResponse> &
    Pick<BootstrapResponse, 'memberships' | 'pending_onboarding_memberships'>,
): BootstrapResponse {
  return {
    authenticated: true,
    user: {
      id: 'user-1',
      username: 'owner',
      email: 'owner@example.com',
      identity_type: 'email',
      first_name: 'Owner',
      last_name: 'One',
    },
    active_membership: null,
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
    ...partial,
  }
}

describe('resolveUniqueOrganizationId', () => {
  it('accepts a single organization from memberships', () => {
    const result = resolveUniqueOrganizationId(
      bootstrapFixture({
        memberships: [
          {
            id: 'm1',
            establishment_id: 'e1',
            establishment_name: 'A',
            organization_id: 'org-1',
            organization_name: 'Org',
            role: 'owner',
            status: 'active',
            scopes: [],
            scope_summary: { business_unit_count: 0 },
          },
        ],
        pending_onboarding_memberships: [],
      }),
    )
    expect(result).toEqual({ ok: true, organizationId: 'org-1' })
  })

  it('accepts a single organization from pending onboarding only', () => {
    const result = resolveUniqueOrganizationId(
      bootstrapFixture({
        memberships: [],
        pending_onboarding_memberships: [
          {
            id: 'm1',
            establishment_id: 'e1',
            establishment_name: 'Draft',
            establishment_status: 'draft',
            organization_id: 'org-draft',
            organization_name: 'Draft Org',
            role: 'owner',
            onboarding_session_id: 's1',
            can_continue_onboarding: true,
          },
        ],
      }),
    )
    expect(result).toEqual({ ok: true, organizationId: 'org-draft' })
  })

  it('dedupes the same organization across sources', () => {
    const result = resolveUniqueOrganizationId(
      bootstrapFixture({
        memberships: [
          {
            id: 'm1',
            establishment_id: 'e1',
            establishment_name: 'A',
            organization_id: 'org-1',
            organization_name: 'Org',
            role: 'owner',
            status: 'active',
            scopes: [],
            scope_summary: { business_unit_count: 0 },
          },
        ],
        pending_onboarding_memberships: [
          {
            id: 'm2',
            establishment_id: 'e2',
            establishment_name: 'Draft',
            establishment_status: 'draft',
            organization_id: 'org-1',
            organization_name: 'Org',
            role: 'owner',
            onboarding_session_id: null,
            can_continue_onboarding: true,
          },
        ],
      }),
    )
    expect(result).toEqual({ ok: true, organizationId: 'org-1' })
  })

  it('rejects zero organizations', () => {
    expect(
      resolveUniqueOrganizationId(
        bootstrapFixture({
          memberships: [],
          pending_onboarding_memberships: [],
        }),
      ),
    ).toEqual({ ok: false, reason: 'none' })
  })

  it('rejects ambiguous organizations without picking the first', () => {
    const result = resolveUniqueOrganizationId(
      bootstrapFixture({
        memberships: [
          {
            id: 'm1',
            establishment_id: 'e1',
            establishment_name: 'A',
            organization_id: 'org-1',
            organization_name: 'Org 1',
            role: 'owner',
            status: 'active',
            scopes: [],
            scope_summary: { business_unit_count: 0 },
          },
          {
            id: 'm2',
            establishment_id: 'e2',
            establishment_name: 'B',
            organization_id: 'org-2',
            organization_name: 'Org 2',
            role: 'owner',
            status: 'active',
            scopes: [],
            scope_summary: { business_unit_count: 0 },
          },
        ],
        pending_onboarding_memberships: [],
      }),
    )
    expect(result).toEqual({ ok: false, reason: 'ambiguous' })
  })
})
