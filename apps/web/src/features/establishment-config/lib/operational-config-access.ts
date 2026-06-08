const OPERATIONAL_CONFIG_ROLES = new Set(['owner', 'director'])

export function canAccessOperationalConfig(role: string | null | undefined): boolean {
  return Boolean(role && OPERATIONAL_CONFIG_ROLES.has(role))
}
