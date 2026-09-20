import type { components } from '@/api/generated/types'

export type ActivationBlocker = {
  code: string
  message: string
}

export type CatalogBusinessUnitSuggestion = components['schemas']['CatalogBusinessUnitSuggestion']
export type CatalogActivitySubjectSuggestion =
  components['schemas']['CatalogActivitySubjectSuggestion']
export type OnboardingDraftResponse = components['schemas']['OnboardingDraftResponse']
export type OnboardingDraftUpdateRequest = components['schemas']['OnboardingDraftUpdateRequest']
export type OnboardingDraftValidation = components['schemas']['OnboardingDraftValidation']
export type OnboardingDraftValidationErrorItem =
  components['schemas']['OnboardingDraftValidationErrorItem']
