import type { components } from '@/api/generated/types'

export type ActivationBlocker = {
  code: string
  message: string
}

export type CatalogBusinessUnitSuggestion = components['schemas']['CatalogBusinessUnitSuggestion']
export type CatalogActivitySubjectSuggestion =
  components['schemas']['CatalogActivitySubjectSuggestion']
export type OnboardingDraftResponse = components['schemas']['OnboardingDraftResponse']
