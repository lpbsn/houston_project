import {
  buildOperationalConfigFallbackPath,
  buildOperationalConfigPath,
} from '@/features/organization/lib/operational-config-navigation'

export type OnboardingOperationalRedirectInput = {
  hasOperationalAccess: boolean
  activeEstablishmentId: string | null | undefined
  routeEstablishmentId: string | null | undefined
}

export function shouldRedirectOnboardingToOperationalConfig(
  input: OnboardingOperationalRedirectInput,
): boolean {
  return (
    input.hasOperationalAccess &&
    Boolean(input.routeEstablishmentId) &&
    input.activeEstablishmentId === input.routeEstablishmentId
  )
}

export function resolveOnboardingOperationalLeavePath({
  establishmentId,
  isDesktop,
}: {
  establishmentId: string
  isDesktop: boolean
}): string {
  return isDesktop
    ? buildOperationalConfigPath(establishmentId)
    : buildOperationalConfigFallbackPath(establishmentId)
}
