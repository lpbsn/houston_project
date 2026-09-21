import type { BootstrapResponse } from '@/features/auth/types'

export type AuthRoutingSession = {
  bootstrap: BootstrapResponse | null
  hasOperationalAccess: boolean
  memberships: BootstrapResponse['memberships']
  sessionEstablishmentId: string | null
}

/**
 * Auth-routing peek only. `switchEstablishment` writes bootstrap into the Query
 * cache before AuthProvider re-renders; guards must not treat that as a second store.
 */
export function resolveAuthRoutingSession(
  cachedBootstrap: BootstrapResponse | undefined,
  fallbackBootstrap: BootstrapResponse | null,
): AuthRoutingSession {
  const bootstrap = cachedBootstrap ?? fallbackBootstrap

  return {
    bootstrap,
    hasOperationalAccess: Boolean(bootstrap?.active_membership),
    memberships: bootstrap?.memberships ?? [],
    sessionEstablishmentId: bootstrap?.active_membership?.establishment_id ?? null,
  }
}
