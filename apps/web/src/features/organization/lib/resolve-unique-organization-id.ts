import type { BootstrapResponse } from '@/features/auth/types'

export type ResolveUniqueOrganizationIdResult =
  | { ok: true; organizationId: string }
  | { ok: false; reason: 'none' | 'ambiguous' }

type OrganizationIdSource = {
  organization_id?: string | null
}

/**
 * Deduplicate organization ids from bootstrap membership sources.
 * Accepts only when exactly one distinct organization is present.
 */
export function resolveUniqueOrganizationId(
  bootstrap: BootstrapResponse | null | undefined,
): ResolveUniqueOrganizationIdResult {
  if (!bootstrap) {
    return { ok: false, reason: 'none' }
  }

  const sources: OrganizationIdSource[] = [
    ...(bootstrap.memberships ?? []),
    ...(bootstrap.pending_onboarding_memberships ?? []),
  ]

  const uniqueIds = new Set<string>()
  for (const source of sources) {
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
