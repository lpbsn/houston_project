import { mapInvitationErrorMessage } from '@/features/auth/lib/invitation-errors'
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
  duplicate_specific_name: 'Ce nom de pôle est déjà utilisé dans l’établissement.',
  invalid_specific_name: 'Ce nom de pôle n’est pas valide.',
  business_unit_without_subjects: 'Chaque pôle doit avoir au moins un sujet.',
  missing_custom_subject_label: 'Le sujet libre doit avoir un libellé.',
  catalog_subject_business_unit_mismatch:
    'Ce sujet n’appartient pas au pôle catalogue sélectionné.',
  missing_director: 'Renseignez le directeur (prénom, nom et email).',
  missing_email: 'L’email est obligatoire.',
  missing_first_name: 'Le prénom est obligatoire.',
  missing_last_name: 'Le nom est obligatoire.',
  invalid_member_role: 'Choisissez un rôle manager ou équipier.',
  duplicate_team_email: 'Cet email est déjà utilisé dans l’équipe.',
  invalid_member: 'Complétez les membres commencés et assignez au moins un pôle.',
  missing_member_business_units: 'Assignez au moins un pôle à ce membre.',
  runtime_already_materialized:
    'La configuration runtime existe déjà pour cet établissement.',
  establishment_already_active: 'Cet établissement est déjà actif.',
  onboarding_draft_invalid: 'Le brouillon d’onboarding est invalide.',
  activation_readiness_failed: 'L’activation a échoué (prérequis incomplets).',
  director_invitation_already_exists: 'Une invitation directeur existe déjà.',
  duplicate_establishment_name: 'Ce nom d’établissement est déjà utilisé.',
  activation_not_ready: 'L’activation a échoué (prérequis incomplets).',
  invalid_onboarding_state: 'Cet onboarding ne peut plus être modifié ou finalisé.',
  draft_not_found: 'Le brouillon d’onboarding est introuvable.',
  catalog_business_unit_inactive: 'Ce pôle du catalogue n’est plus actif.',
  catalog_activity_subject_inactive: 'Ce sujet du catalogue n’est plus actif.',
  unknown_catalog_key: 'Sélectionnez un pôle depuis le catalogue.',
  invalid_organization_name: 'Le nom de l’organisation est invalide.',
}

export function messageForDraftErrorCode(code: string): string {
  return CODE_MESSAGES[code] ?? code
}

export function messagesForDraftField(
  errors: OnboardingDraftValidationErrorItem[],
  target: { section: string; field?: string | null; key?: string | null },
): string[] {
  const targetField = target.field ?? null
  const targetKey = target.key ?? null
  return errors
    .filter((error) => {
      if ((error.section ?? '') !== target.section) {
        return false
      }
      if ((error.field ?? null) !== targetField) {
        return false
      }
      return (error.key ?? null) === targetKey
    })
    .map((error) => messageForDraftErrorCode(error.code))
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

const INVITATION_ERROR_CODES = new Set([
  'membership_invitation_user_exists',
  'membership_invitation_duplicate',
  'membership_invitation_owner_conflict',
  'organizational_owner_invariant_conflict',
  'membership_invitation_role_not_allowed',
  'membership_invitation_invalid',
  'director_invitation_already_exists',
  'director_invitation_owner_not_allowed',
])

function detailedDraftMessages(error: unknown): string[] {
  const record = error && typeof error === 'object' ? (error as OnboardingApiError) : null
  const fromPayload = extractDraftValidationErrors(record?.payload)
  const fromError = extractDraftValidationErrors(error)
  const items = fromPayload.length > 0 ? fromPayload : fromError
  return [...new Set(items.map((item) => messageForDraftErrorCode(item.code)))]
}

export function getCompleteErrorMessage(error: unknown, fallback: string): string {
  const detailed = detailedDraftMessages(error)
  if (detailed.length > 0) {
    return detailed.join(' ')
  }
  const record = error && typeof error === 'object' ? (error as OnboardingApiError) : null
  const code = record && typeof record.code === 'string' ? record.code : ''
  const detail = record && typeof record.detail === 'string' ? record.detail : ''
  if (code.length > 0 && code in CODE_MESSAGES) {
    return CODE_MESSAGES[code]
  }
  if (code.length > 0 && INVITATION_ERROR_CODES.has(code)) {
    return mapInvitationErrorMessage(code, detail)
  }
  if (detail.length > 0) {
    return detail
  }
  if (error instanceof Error && error.message) {
    return error.message
  }
  return fallback
}
