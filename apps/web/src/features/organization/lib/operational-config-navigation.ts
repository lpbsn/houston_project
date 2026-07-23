const ESTABLISHMENT_ADMIN_RETURN_PATH =
  /^\/organization\/establishments\/[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i

export function isValidEstablishmentAdminReturnTo(returnTo: string | null | undefined): boolean {
  if (!returnTo) {
    return false
  }
  return ESTABLISHMENT_ADMIN_RETURN_PATH.test(returnTo)
}

export function buildOperationalConfigPath(establishmentId: string): string {
  const returnTo = `/organization/establishments/${establishmentId}`
  return `/app/operational-config?returnTo=${encodeURIComponent(returnTo)}`
}

export function resolveOperationalConfigReturnPath({
  returnTo,
  activeEstablishmentId,
  canAccessActiveEstablishmentAdmin,
}: {
  returnTo: string | null | undefined
  activeEstablishmentId: string | null | undefined
  canAccessActiveEstablishmentAdmin: boolean
}): string {
  if (isValidEstablishmentAdminReturnTo(returnTo)) {
    return returnTo!
  }

  if (activeEstablishmentId && canAccessActiveEstablishmentAdmin) {
    return `/organization/establishments/${activeEstablishmentId}`
  }

  return '/reporting'
}

export type OpenOperationalConfigResult =
  | { kind: 'needs_switch'; establishmentId: string; path: string }
  | { kind: 'already_selected'; path: string }

export function planOpenOperationalConfig({
  targetEstablishmentId,
  activeEstablishmentId,
}: {
  targetEstablishmentId: string
  activeEstablishmentId: string | null | undefined
}): OpenOperationalConfigResult {
  const path = buildOperationalConfigPath(targetEstablishmentId)
  if (activeEstablishmentId === targetEstablishmentId) {
    return { kind: 'already_selected', path }
  }
  return { kind: 'needs_switch', establishmentId: targetEstablishmentId, path }
}
