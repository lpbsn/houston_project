import { describe, expect, it } from 'vitest'

import {
  getTeamMemberScopeLabels,
  groupTeamMembersByRole,
  matchesTeamMemberSearch,
  shouldShowTeamMemberScopeBadges,
} from '@/features/auth/lib/team-members'
import type { EstablishmentMembershipResponse } from '@/features/auth/types'

function member(
  overrides: Partial<EstablishmentMembershipResponse> & Pick<EstablishmentMembershipResponse, 'id' | 'role'>,
): EstablishmentMembershipResponse {
  return {
    establishment_id: 'est-1',
    establishment_name: 'Nice',
    organization_id: 'org-1',
    organization_name: 'Org',
    status: 'active',
    scopes: [],
    scope_summary: { business_unit_count: 0 },
    permission_hints: {
      can_edit_role: false,
      can_edit_scopes: false,
      can_edit_status: false,
      can_edit_personal_info: false,
    },
    user: {
      id: 'user-1',
      display_name: 'Alice Martin',
      username: 'alice',
      email: 'alice@example.com',
      first_name: 'Alice',
      last_name: 'Martin',
    },
    ...overrides,
  }
}

describe('team-members', () => {
  it('groups members by role and filters by search query', () => {
    const memberships = [
      member({
        id: '1',
        role: 'manager',
        user: {
          id: 'user-2',
          display_name: 'Bob Lee',
          username: 'bob',
          email: 'bob@example.com',
          first_name: 'Bob',
          last_name: 'Lee',
        },
      }),
      member({ id: '2', role: 'staff' }),
    ]

    const sections = groupTeamMembersByRole(memberships, 'alice')

    expect(sections).toHaveLength(1)
    expect(sections[0]?.role).toBe('staff')
    expect(sections[0]?.members).toHaveLength(1)
    expect(matchesTeamMemberSearch(memberships[0]!, 'alice')).toBe(false)
  })

  it('returns scope labels only for manager and staff', () => {
    const scopedMembership = member({
      id: '3',
      role: 'manager',
      scopes: [
        {
          scope_id: 'scope-1',
          scope_type: 'business_unit',
          scope_label: 'Housekeeping',
        },
        {
          scope_id: 'scope-2',
          scope_type: 'business_unit',
          scope_label: 'Restaurant',
        },
      ],
    })

    expect(shouldShowTeamMemberScopeBadges('manager')).toBe(true)
    expect(shouldShowTeamMemberScopeBadges('staff')).toBe(true)
    expect(shouldShowTeamMemberScopeBadges('director')).toBe(false)
    expect(getTeamMemberScopeLabels(scopedMembership)).toEqual(['Housekeeping', 'Restaurant'])
    expect(getTeamMemberScopeLabels(member({ id: '4', role: 'director' }))).toEqual([])
  })

  it('matches search query against scope labels', () => {
    const scopedMembership = member({
      id: '5',
      role: 'staff',
      scopes: [
        {
          scope_id: 'scope-1',
          scope_type: 'business_unit',
          scope_label: 'Spa',
        },
      ],
    })

    expect(matchesTeamMemberSearch(scopedMembership, 'spa')).toBe(true)
  })
})
