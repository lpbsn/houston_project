import type { EstablishmentMembershipResponse, RoleEnum } from '@/features/auth/types'
import { formatMembershipRoleDisplay } from '@/lib/display-names'

export type TeamRoleSection = {
  role: RoleEnum
  label: string
  members: EstablishmentMembershipResponse[]
}

const TEAM_ROLE_ORDER: RoleEnum[] = ['owner', 'director', 'manager', 'staff']

const TEAM_SECTION_LABELS: Record<RoleEnum, string> = {
  owner: 'PROPRIÉTAIRES',
  director: 'DIRECTEURS',
  manager: 'MANAGERS',
  staff: 'STAFF',
}

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

export function groupTeamMembersByRole(
  memberships: EstablishmentMembershipResponse[],
  query: string,
): TeamRoleSection[] {
  const filtered = memberships.filter((membership) => matchesTeamMemberSearch(membership, query))

  return TEAM_ROLE_ORDER.map((role) => ({
    role,
    label: getTeamSectionLabel(role),
    members: filtered.filter((membership) => normalizeTeamRole(membership.role) === role),
  })).filter((section) => section.members.length > 0)
}

export function membershipIsActive(membership: EstablishmentMembershipResponse): boolean {
  return membership.status === 'active'
}

export function membershipIsInvited(membership: EstablishmentMembershipResponse): boolean {
  return membership.status === 'invited'
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
