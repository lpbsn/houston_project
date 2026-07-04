const MEMBERSHIP_ROLE_LABELS: Record<string, string> = {
  owner: 'Propriétaire',
  director: 'Directeur',
  manager: 'Manager',
  staff: 'Équipe',
}

export function formatMembershipRoleDisplay(role: string): string {
  return MEMBERSHIP_ROLE_LABELS[role] ?? role
}

export function getDisplayNameInitials(displayName: string): string {
  const trimmed = displayName.trim()
  if (!trimmed) {
    return '?'
  }

  const parts = trimmed.split(/\s+/).filter(Boolean)
  if (parts.length >= 2) {
    const firstInitial = parts[0][0] ?? ''
    const lastInitial = parts[parts.length - 1].replace(/\.$/, '')[0] ?? ''
    const initials = `${firstInitial}${lastInitial}`.toUpperCase()
    return initials || '?'
  }

  return trimmed.slice(0, 2).toUpperCase()
}
