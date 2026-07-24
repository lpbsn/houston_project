import { describe, expect, it } from 'vitest'

import {
  countTeamMembersByStatus,
  getTeamMemberScopeLabels,
  getTeamMembershipStatusBadge,
  getTeamSectionLabel,
  groupTeamMembersByRole,
  matchesTeamMemberSearch,
  matchesTeamMemberStatusFilter,
  shouldShowTeamMemberScopeBadges,
  toggleTeamMemberStatusFilter,
  type TeamMembershipStatus,
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
      can_reinvite: false,
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

  it('does not match search against status labels', () => {
    expect(matchesTeamMemberSearch(member({ id: 'a1', role: 'staff', status: 'active' }), 'actif')).toBe(
      false,
    )
    expect(
      matchesTeamMemberSearch(member({ id: 'a2', role: 'staff', status: 'deactivated' }), 'inactif'),
    ).toBe(false)
    expect(
      matchesTeamMemberSearch(member({ id: 'a3', role: 'staff', status: 'invited' }), 'invité'),
    ).toBe(false)
  })

  it('groups multiple owners and directors without uniqueness assumptions', () => {
    const memberships = [
      member({ id: 'o1', role: 'owner' }),
      member({
        id: 'o2',
        role: 'owner',
        user: {
          id: 'user-o2',
          display_name: 'Other Owner',
          username: 'other',
          email: 'other@example.com',
          first_name: 'Other',
          last_name: 'Owner',
        },
      }),
      member({ id: 'd1', role: 'director' }),
      member({
        id: 'd2',
        role: 'director',
        user: {
          id: 'user-d2',
          display_name: 'Second Director',
          username: 'dir2',
          email: 'dir2@example.com',
          first_name: 'Second',
          last_name: 'Director',
        },
      }),
    ]

    const sections = groupTeamMembersByRole(memberships, '')

    expect(getTeamSectionLabel('owner')).toBe('PROPRIÉTAIRES')
    expect(getTeamSectionLabel('director')).toBe('DIRECTEURS')
    expect(sections.find((section) => section.role === 'owner')?.members).toHaveLength(2)
    expect(sections.find((section) => section.role === 'director')?.members).toHaveLength(2)
  })

  it('returns status badges only for deactivated and invited members', () => {
    expect(getTeamMembershipStatusBadge(member({ id: 'b1', role: 'staff', status: 'active' }))).toBeNull()
    expect(getTeamMembershipStatusBadge(member({ id: 'b2', role: 'staff', status: 'deactivated' }))).toEqual(
      { label: 'Inactif', variant: 'gray' },
    )
    expect(getTeamMembershipStatusBadge(member({ id: 'b3', role: 'staff', status: 'invited' }))).toEqual({
      label: 'Invité',
      variant: 'amber',
    })
  })

  it('counts memberships by status globally', () => {
    const counts = countTeamMembersByStatus([
      member({ id: 'c1', role: 'staff', status: 'active' }),
      member({ id: 'c2', role: 'staff', status: 'active' }),
      member({ id: 'c3', role: 'manager', status: 'deactivated' }),
      member({ id: 'c4', role: 'staff', status: 'invited' }),
    ])

    expect(counts).toEqual({ total: 4, active: 2, deactivated: 1, invited: 1 })
  })

  it('filters by selected statuses with OR logic and empty set as Tous', () => {
    const active = member({ id: 'f1', role: 'staff', status: 'active' })
    const deactivated = member({ id: 'f2', role: 'staff', status: 'deactivated' })
    const invited = member({ id: 'f3', role: 'staff', status: 'invited' })

    expect(matchesTeamMemberStatusFilter(active, new Set())).toBe(true)
    expect(matchesTeamMemberStatusFilter(deactivated, new Set())).toBe(true)

    const inactiveAndInvited = new Set<TeamMembershipStatus>(['deactivated', 'invited'])
    expect(matchesTeamMemberStatusFilter(active, inactiveAndInvited)).toBe(false)
    expect(matchesTeamMemberStatusFilter(deactivated, inactiveAndInvited)).toBe(true)
    expect(matchesTeamMemberStatusFilter(invited, inactiveAndInvited)).toBe(true)
  })

  it('combines status filters and search with AND logic and drops empty groups', () => {
    const memberships = [
      member({
        id: 'g1',
        role: 'manager',
        status: 'deactivated',
        user: {
          id: 'user-g1',
          display_name: 'Martin Lee',
          username: 'martin',
          email: 'martin@example.com',
          first_name: 'Martin',
          last_name: 'Lee',
        },
      }),
      member({
        id: 'g2',
        role: 'staff',
        status: 'invited',
        user: {
          id: 'user-g2',
          display_name: 'Martin Invited',
          username: 'minv',
          email: 'minv@example.com',
          first_name: 'Martin',
          last_name: 'Invited',
        },
      }),
      member({
        id: 'g3',
        role: 'staff',
        status: 'active',
        user: {
          id: 'user-g3',
          display_name: 'Martin Active',
          username: 'mact',
          email: 'mact@example.com',
          first_name: 'Martin',
          last_name: 'Active',
        },
      }),
      member({
        id: 'g4',
        role: 'director',
        status: 'deactivated',
        user: {
          id: 'user-g4',
          display_name: 'Other',
          username: 'other',
          email: 'other@example.com',
          first_name: 'Other',
          last_name: 'Person',
        },
      }),
    ]

    const sections = groupTeamMembersByRole(
      memberships,
      'Martin',
      new Set<TeamMembershipStatus>(['deactivated', 'invited']),
    )

    expect(sections).toHaveLength(2)
    expect(sections.find((section) => section.role === 'manager')?.members).toHaveLength(1)
    expect(sections.find((section) => section.role === 'staff')?.members).toHaveLength(1)
    expect(sections.find((section) => section.role === 'director')).toBeUndefined()
  })

  it('toggles status filters by recreating the set', () => {
    const initial = new Set<TeamMembershipStatus>(['active'])
    const withInvited = toggleTeamMemberStatusFilter(initial, 'invited')
    const withoutActive = toggleTeamMemberStatusFilter(withInvited, 'active')

    expect(withInvited).not.toBe(initial)
    expect([...withInvited].sort()).toEqual(['active', 'invited'])
    expect([...withoutActive]).toEqual(['invited'])
    expect(initial.has('invited')).toBe(false)
  })
})
