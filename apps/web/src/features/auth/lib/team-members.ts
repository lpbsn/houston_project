import type { EstablishmentMembershipResponse, RoleEnum } from '@/features/auth/types'
import { formatMembershipRoleDisplay } from '@/lib/display-names'
import type { HoustonBadgeVariant } from '@/lib/terrain-styles'

export type TeamRoleSection = {
  role: RoleEnum
  label: string
  members: EstablishmentMembershipResponse[]
}

export type TeamMembershipStatus = 'active' | 'deactivated' | 'invited'

export type TeamMembershipStatusBadge = {
  label: string
  variant: HoustonBadgeVariant
}

export type TeamMemberStatusCounts = {
  total: number
  active: number
  deactivated: number
  invited: number
}

const TEAM_ROLE_ORDER: RoleEnum[] = ['owner', 'director', 'manager', 'staff']

const TEAM_SECTION_LABELS: Record<RoleEnum, string> = {
  owner: 'PROPRIÉTAIRES',
  director: 'DIRECTEURS',
  manager: 'MANAGERS',
  staff: 'STAFF',
}

const TEAM_MEMBERSHIP_STATUSES: readonly TeamMembershipStatus[] = [
  'active',
  'deactivated',
  'invited',
]

export function normalizeTeamRole(role: string | null | undefined): RoleEnum {
  return TEAM_ROLE_ORDER.find((candidate) => candidate === role) ?? 'staff'
}

export function getTeamSectionLabel(role: RoleEnum): string {
  return TEAM_SECTION_LABELS[role]
}

export function buildMemberDisplayName(membership: EstablishmentMembershipResponse): string {
  const firstName = membership.user.first_name?.trim()
  const lastName = membership.user.last_name?.trim()
  const parts = [firstName, lastName].filter(Boolean)
  if (parts.length > 0) {
    return parts.join(' ')
  }
  return membership.user.display_name
}

export function matchesTeamMemberSearch(
  membership: EstablishmentMembershipResponse,
  query: string,
): boolean {
  const normalized = query.trim().toLowerCase()
  if (!normalized) {
    return true
  }

  const haystack = [
    membership.user.first_name,
    membership.user.last_name,
    membership.user.display_name,
    membership.user.email,
    membership.user.username,
    formatMembershipRoleDisplay(membership.role),
    ...getTeamMemberScopeLabels(membership),
  ]
    .filter(Boolean)
    .join(' ')
    .toLowerCase()

  return haystack.includes(normalized)
}

export function normalizeTeamMembershipStatus(
  status: string | null | undefined,
): TeamMembershipStatus | null {
  return TEAM_MEMBERSHIP_STATUSES.find((candidate) => candidate === status) ?? null
}

export function membershipIsActive(membership: EstablishmentMembershipResponse): boolean {
  return membership.status === 'active'
}

export function membershipIsInvited(membership: EstablishmentMembershipResponse): boolean {
  return membership.status === 'invited'
}

export function membershipIsDeactivated(membership: EstablishmentMembershipResponse): boolean {
  return membership.status === 'deactivated'
}

export function getTeamMembershipStatusBadge(
  membership: EstablishmentMembershipResponse,
): TeamMembershipStatusBadge | null {
  if (membershipIsDeactivated(membership)) {
    return { label: 'Inactif', variant: 'gray' }
  }
  if (membershipIsInvited(membership)) {
    return { label: 'Invité', variant: 'amber' }
  }
  return null
}

export function matchesTeamMemberStatusFilter(
  membership: EstablishmentMembershipResponse,
  selectedStatuses: ReadonlySet<TeamMembershipStatus>,
): boolean {
  if (selectedStatuses.size === 0) {
    return true
  }
  const status = normalizeTeamMembershipStatus(membership.status)
  return status !== null && selectedStatuses.has(status)
}

export function countTeamMembersByStatus(
  memberships: EstablishmentMembershipResponse[],
): TeamMemberStatusCounts {
  let active = 0
  let deactivated = 0
  let invited = 0

  for (const membership of memberships) {
    if (membershipIsActive(membership)) {
      active += 1
    } else if (membershipIsDeactivated(membership)) {
      deactivated += 1
    } else if (membershipIsInvited(membership)) {
      invited += 1
    }
  }

  return {
    total: memberships.length,
    active,
    deactivated,
    invited,
  }
}

export function toggleTeamMemberStatusFilter(
  selectedStatuses: ReadonlySet<TeamMembershipStatus>,
  status: TeamMembershipStatus,
): ReadonlySet<TeamMembershipStatus> {
  const next = new Set(selectedStatuses)
  if (next.has(status)) {
    next.delete(status)
  } else {
    next.add(status)
  }
  return next
}

export function groupTeamMembersByRole(
  memberships: EstablishmentMembershipResponse[],
  query: string,
  selectedStatuses: ReadonlySet<TeamMembershipStatus> = new Set(),
): TeamRoleSection[] {
  const filtered = memberships.filter(
    (membership) =>
      matchesTeamMemberStatusFilter(membership, selectedStatuses) &&
      matchesTeamMemberSearch(membership, query),
  )

  return TEAM_ROLE_ORDER.map((role) => ({
    role,
    label: getTeamSectionLabel(role),
    members: filtered.filter((membership) => normalizeTeamRole(membership.role) === role),
  })).filter((section) => section.members.length > 0)
}

export function shouldShowTeamMemberScopeBadges(role: string | null | undefined): boolean {
  const normalized = normalizeTeamRole(role)
  return normalized === 'manager' || normalized === 'staff'
}

export function getTeamMemberScopeLabels(membership: EstablishmentMembershipResponse): string[] {
  if (!shouldShowTeamMemberScopeBadges(membership.role)) {
    return []
  }

  const labels = membership.scopes
    .map((scope) => scope.scope_label?.trim() || scope.scope_id)
    .filter((label): label is string => Boolean(label))

  return [...new Set(labels)]
}
