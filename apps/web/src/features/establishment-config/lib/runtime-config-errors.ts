import { RuntimeConfigApiError } from '@/features/establishment-config/api'

export function mapRuntimeConfigConflictMessage(
  code: string | null | undefined,
  fallbackDetail?: string | null,
): string {
  switch (code) {
    case 'last_active_business_unit':
      return 'Vous devez conserver au moins un pôle actif.'
    case 'last_active_activity_subject':
      return 'Chaque pôle doit conserver au moins un sujet actif.'
    case 'business_unit_has_membership_scopes':
      return 'Retirez d’abord les périmètres membres associés à ce pôle avant de le retirer.'
    case 'duplicate_business_unit_key':
    case 'duplicate_specific_name':
      return 'Un pôle avec ce libellé existe déjà.'
    case 'duplicate_activity_subject_normalized_name':
    case 'duplicate_activity_subject_routing_key':
      return 'Un sujet avec ce libellé existe déjà. Réactivez le sujet inactif si besoin.'
    case 'activity_subject_already_active':
      return 'Ce sujet est déjà actif.'
    case 'business_unit_inactive':
      return 'Réactivez d’abord le pôle parent avant de réactiver ce sujet.'
    default:
      return fallbackDetail?.trim() || 'Une erreur est survenue.'
  }
}

export function resolveRuntimeConfigErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof RuntimeConfigApiError) {
    return mapRuntimeConfigConflictMessage(error.code, error.message)
  }

  return fallback
}
