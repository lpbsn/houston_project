import { describe, expect, it } from 'vitest'

import type { BootstrapResponse } from '@/features/auth/types'

import {
  canManageOrganizationOfEstablishment,
  resolveOrganizationIdForEstablishment,
} from './resolve-organization-id-for-establishment'

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

describe('resolveOrganizationIdForEstablishment', () => {
  it('resolves from an active membership that matches the establishment', () => {
    const result = resolveOrganizationIdForEstablishment(
      bootstrapFixture({
        memberships: [],
        pending_onboarding_memberships: [],
        active_membership: {
          id: 'm-active',
          establishment_id: 'est-1',
          establishment_name: 'A',
          organization_id: 'org-active',
          organization_name: 'Org',
          role: 'owner',
          status: 'active',
          scopes: [],
          scope_summary: { business_unit_count: 0 },
        },
      }),
      'est-1',
    )
    expect(result).toEqual({ ok: true, organizationId: 'org-active' })
  })

  it('resolves from memberships', () => {
    const result = resolveOrganizationIdForEstablishment(
      bootstrapFixture({
        memberships: [
          {
            id: 'm1',
            establishment_id: 'est-1',
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
      'est-1',
    )
    expect(result).toEqual({ ok: true, organizationId: 'org-1' })
  })

  it('resolves from pending onboarding memberships', () => {
    const result = resolveOrganizationIdForEstablishment(
      bootstrapFixture({
        memberships: [],
        pending_onboarding_memberships: [
          {
            id: 'm1',
            establishment_id: 'est-draft',
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
      'est-draft',
    )
    expect(result).toEqual({ ok: true, organizationId: 'org-draft' })
  })

  it('picks the organization of the targeted establishment when several orgs exist', () => {
    const result = resolveOrganizationIdForEstablishment(
      bootstrapFixture({
        memberships: [
          {
            id: 'm1',
            establishment_id: 'est-1',
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
            establishment_id: 'est-2',
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
      'est-2',
    )
    expect(result).toEqual({ ok: true, organizationId: 'org-2' })
  })

  it('rejects an unknown establishment without inferring another organization', () => {
    const result = resolveOrganizationIdForEstablishment(
      bootstrapFixture({
        memberships: [
          {
            id: 'm1',
            establishment_id: 'est-1',
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
            establishment_id: 'est-2',
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
      'est-missing',
    )
    expect(result).toEqual({ ok: false, reason: 'none' })
  })

  it('rejects zero matching sources', () => {
    expect(
      resolveOrganizationIdForEstablishment(
        bootstrapFixture({
          memberships: [],
          pending_onboarding_memberships: [],
        }),
        'est-1',
      ),
    ).toEqual({ ok: false, reason: 'none' })
  })

  it('rejects conflicting organizations for the same establishment', () => {
    const result = resolveOrganizationIdForEstablishment(
      bootstrapFixture({
        memberships: [
          {
            id: 'm1',
            establishment_id: 'est-1',
            establishment_name: 'A',
            organization_id: 'org-1',
            organization_name: 'Org 1',
            role: 'owner',
            status: 'active',
            scopes: [],
            scope_summary: { business_unit_count: 0 },
          },
        ],
        pending_onboarding_memberships: [
          {
            id: 'm2',
            establishment_id: 'est-1',
            establishment_name: 'A',
            establishment_status: 'draft',
            organization_id: 'org-2',
            organization_name: 'Org 2',
            role: 'owner',
            onboarding_session_id: null,
            can_continue_onboarding: true,
          },
        ],
      }),
      'est-1',
    )
    expect(result).toEqual({ ok: false, reason: 'ambiguous' })
  })
})

describe('canManageOrganizationOfEstablishment', () => {
  it('is true when the actor is owner on the current establishment', () => {
    expect(
      canManageOrganizationOfEstablishment(
        bootstrapFixture({
          memberships: [],
          pending_onboarding_memberships: [],
          active_membership: {
            id: 'm-active',
            establishment_id: 'est-1',
            establishment_name: 'A',
            organization_id: 'org-1',
            organization_name: 'Org',
            role: 'owner',
            status: 'active',
            scopes: [],
            scope_summary: { business_unit_count: 0 },
          },
        }),
        'est-1',
      ),
    ).toBe(true)
  })

  it('is true when the actor is owner on another establishment of the same org', () => {
    expect(
      canManageOrganizationOfEstablishment(
        bootstrapFixture({
          memberships: [
            {
              id: 'm-owner',
              establishment_id: 'est-a',
              establishment_name: 'A',
              organization_id: 'org-1',
              organization_name: 'Org',
              role: 'owner',
              status: 'active',
              scopes: [],
              scope_summary: { business_unit_count: 0 },
            },
            {
              id: 'm-staff',
              establishment_id: 'est-1',
              establishment_name: 'B',
              organization_id: 'org-1',
              organization_name: 'Org',
              role: 'staff',
              status: 'active',
              scopes: [],
              scope_summary: { business_unit_count: 0 },
            },
          ],
          pending_onboarding_memberships: [],
        }),
        'est-1',
      ),
    ).toBe(true)
  })

  it('is true when the actor is owner on a pending draft of the same org', () => {
    expect(
      canManageOrganizationOfEstablishment(
        bootstrapFixture({
          memberships: [
            {
              id: 'm-staff',
              establishment_id: 'est-1',
              establishment_name: 'B',
              organization_id: 'org-1',
              organization_name: 'Org',
              role: 'staff',
              status: 'active',
              scopes: [],
              scope_summary: { business_unit_count: 0 },
            },
          ],
          pending_onboarding_memberships: [
            {
              id: 'm-draft',
              establishment_id: 'est-draft',
              establishment_name: 'Draft',
              establishment_status: 'draft',
              organization_id: 'org-1',
              organization_name: 'Org',
              role: 'owner',
              onboarding_session_id: 's1',
              can_continue_onboarding: true,
            },
          ],
        }),
        'est-1',
      ),
    ).toBe(true)
  })

  it('is false when the actor is owner only on a different organization', () => {
    expect(
      canManageOrganizationOfEstablishment(
        bootstrapFixture({
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
          memberships: [
            {
              id: 'm-a',
              establishment_id: 'est-a',
              establishment_name: 'A',
              organization_id: 'org-a',
              organization_name: 'Org A',
              role: 'owner',
              status: 'active',
              scopes: [],
              scope_summary: { business_unit_count: 0 },
            },
            {
              id: 'm-b',
              establishment_id: 'est-1',
              establishment_name: 'B',
              organization_id: 'org-b',
              organization_name: 'Org B',
              role: 'staff',
              status: 'active',
              scopes: [],
              scope_summary: { business_unit_count: 0 },
            },
          ],
          pending_onboarding_memberships: [],
        }),
        'est-1',
      ),
    ).toBe(false)
  })

  it('is false when the actor is only director or staff on the current org', () => {
    expect(
      canManageOrganizationOfEstablishment(
        bootstrapFixture({
          memberships: [
            {
              id: 'm-1',
              establishment_id: 'est-1',
              establishment_name: 'B',
              organization_id: 'org-1',
              organization_name: 'Org',
              role: 'director',
              status: 'active',
              scopes: [],
              scope_summary: { business_unit_count: 0 },
            },
          ],
          pending_onboarding_memberships: [],
        }),
        'est-1',
      ),
    ).toBe(false)
  })

  it('is false when the establishment organization cannot be resolved', () => {
    expect(
      canManageOrganizationOfEstablishment(
        bootstrapFixture({
          memberships: [],
          pending_onboarding_memberships: [],
        }),
        'est-1',
      ),
    ).toBe(false)
    expect(
      canManageOrganizationOfEstablishment(
        bootstrapFixture({
          memberships: [
            {
              id: 'm1',
              establishment_id: 'est-1',
              establishment_name: 'A',
              organization_id: 'org-1',
              organization_name: 'Org 1',
              role: 'owner',
              status: 'active',
              scopes: [],
              scope_summary: { business_unit_count: 0 },
            },
          ],
          pending_onboarding_memberships: [
            {
              id: 'm2',
              establishment_id: 'est-1',
              establishment_name: 'A',
              establishment_status: 'draft',
              organization_id: 'org-2',
              organization_name: 'Org 2',
              role: 'owner',
              onboarding_session_id: null,
              can_continue_onboarding: true,
            },
          ],
        }),
        'est-1',
      ),
    ).toBe(false)
  })
})
