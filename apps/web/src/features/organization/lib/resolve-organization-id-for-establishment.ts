import type { BootstrapResponse } from '@/features/auth/types'

export type ResolveOrganizationIdForEstablishmentResult =
  | { ok: true; organizationId: string }
  | { ok: false; reason: 'none' | 'ambiguous' }

type OrganizationIdSource = {
  establishment_id?: string | null
  organization_id?: string | null
}

/**
 * Resolve the organization of a known establishment from bootstrap membership sources.
 * Does not infer an org when the establishment is absent.
 */
export function resolveOrganizationIdForEstablishment(
  bootstrap: BootstrapResponse | null | undefined,
  establishmentId: string,
): ResolveOrganizationIdForEstablishmentResult {
  if (!bootstrap || establishmentId.length === 0) {
    return { ok: false, reason: 'none' }
  }

  const sources: OrganizationIdSource[] = [
    ...(bootstrap.active_membership ? [bootstrap.active_membership] : []),
    ...(bootstrap.memberships ?? []),
    ...(bootstrap.pending_onboarding_memberships ?? []),
  ]

  const uniqueIds = new Set<string>()
  for (const source of sources) {
    if (source.establishment_id !== establishmentId) {
      continue
    }
    const id = source.organization_id
    if (typeof id === 'string' && id.length > 0) {
      uniqueIds.add(id)
    }
  }

  if (uniqueIds.size === 0) {
    return { ok: false, reason: 'none' }
  }
  if (uniqueIds.size > 1) {
    return { ok: false, reason: 'ambiguous' }
  }

  const [organizationId] = uniqueIds
  return { ok: true, organizationId: organizationId! }
}

type OrganizationCapabilitySource = {
  organization_id?: string | null
  role?: string | null
  status?: string | null
}

/**
 * UX-only: true when bootstrap shows an owner membership on this establishment's org.
 * Does not use the user-global `can_manage_organization` hint.
 */
export function canManageOrganizationOfEstablishment(
  bootstrap: BootstrapResponse | null | undefined,
  establishmentId: string,
): boolean {
  const resolved = resolveOrganizationIdForEstablishment(bootstrap, establishmentId)
  if (!resolved.ok || !bootstrap) {
    return false
  }

  const sources: OrganizationCapabilitySource[] = [
    ...(bootstrap.active_membership ? [bootstrap.active_membership] : []),
    ...(bootstrap.memberships ?? []),
    ...(bootstrap.pending_onboarding_memberships ?? []),
  ]

  return sources.some((source) => {
    if (source.organization_id !== resolved.organizationId) {
      return false
    }
    if (source.role !== 'owner') {
      return false
    }
    if (source.status != null && source.status !== 'active') {
      return false
    }
    return true
  })
}
