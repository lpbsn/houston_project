import type { OnboardingApiError } from '@/features/onboarding/api'

export type OnboardingDraftValidationErrorItem = {
  code: string
  section?: string
  field?: string | null
  key?: string | null
}

export type FieldErrorMap = Record<string, string[]>

function fieldPath(error: OnboardingDraftValidationErrorItem): string {
  const parts = [error.section, error.field, error.key].filter(
    (part): part is string => typeof part === 'string' && part.length > 0,
  )
  return parts.length > 0 ? parts.join('.') : error.code
}

const CODE_MESSAGES: Record<string, string> = {
  missing_establishment_name: 'Le nom de l’établissement est obligatoire.',
  invalid_activity_description_length:
    'La description doit contenir entre 10 et 5 000 caractères.',
  insufficient_business_units: 'Ajoutez au moins un pôle d’activité.',
  missing_catalog_key: 'Sélectionnez un pôle depuis le catalogue.',
  missing_specific_name: 'Le nom du pôle est obligatoire.',
  business_unit_without_subjects: 'Chaque pôle doit avoir au moins un sujet.',
  missing_director: 'Renseignez le directeur (prénom, nom et email).',
  invalid_member: 'Complétez les membres commencés et assignez au moins un pôle.',
  missing_member_business_units: 'Assignez au moins un pôle à ce membre.',
  runtime_already_materialized:
    'La configuration runtime existe déjà pour cet établissement.',
  establishment_already_active: 'Cet établissement est déjà actif.',
  onboarding_draft_invalid: 'Le brouillon d’onboarding est invalide.',
  activation_readiness_failed: 'L’activation a échoué (prérequis incomplets).',
  director_invitation_already_exists: 'Une invitation directeur existe déjà.',
  duplicate_establishment_name: 'Ce nom d’établissement est déjà utilisé.',
}

export function messageForDraftErrorCode(code: string): string {
  return CODE_MESSAGES[code] ?? code
}

export function mapDraftValidationErrors(
  errors: OnboardingDraftValidationErrorItem[] | undefined,
): FieldErrorMap {
  const map: FieldErrorMap = {}
  if (!errors) {
    return map
  }

  for (const error of errors) {
    const path = fieldPath(error)
    const list = map[path] ?? []
    list.push(messageForDraftErrorCode(error.code))
    map[path] = list
  }
  return map
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

export function extractDraftValidationErrors(
  payload: unknown,
): OnboardingDraftValidationErrorItem[] {
  if (!isRecord(payload) || !Array.isArray(payload.errors)) {
    return []
  }

  return payload.errors.filter(
    (error): error is OnboardingDraftValidationErrorItem =>
      isRecord(error) && typeof error.code === 'string',
  )
}

export function getCompleteErrorMessage(error: unknown, fallback: string): string {
  if (error && typeof error === 'object' && 'code' in error) {
    const code = (error as OnboardingApiError).code
    if (typeof code === 'string' && code.length > 0) {
      return messageForDraftErrorCode(code)
    }
  }
  if (error && typeof error === 'object' && 'detail' in error) {
    const detail = (error as OnboardingApiError).detail
    if (typeof detail === 'string' && detail.length > 0) {
      return detail
    }
  }
  if (error instanceof Error && error.message) {
    return error.message
  }
  return fallback
}
