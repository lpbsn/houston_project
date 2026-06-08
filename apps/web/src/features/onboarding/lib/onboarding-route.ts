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
