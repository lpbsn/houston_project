const TECHNICAL_ESTABLISHMENT_NAME_RE = /^draft-/i

/** True when the backend establishment name is a registration temp name. */
export function isTechnicalEstablishmentName(name: string | null | undefined): boolean {
  if (!name) {
    return false
  }
  return TECHNICAL_ESTABLISHMENT_NAME_RE.test(name.trim())
}

/**
 * Safe label for onboarding UI: never show `draft-*` temp names.
 * Prefer organization name, then a neutral fallback.
 */
export function displayEstablishmentName(input: {
  establishmentName?: string | null
  organizationName?: string | null
  fallback?: string
}): string {
  const establishmentName = input.establishmentName?.trim() ?? ''
  if (establishmentName && !isTechnicalEstablishmentName(establishmentName)) {
    return establishmentName
  }

  const organizationName = input.organizationName?.trim() ?? ''
  if (organizationName) {
    return organizationName
  }

  return input.fallback ?? 'Votre établissement'
}
