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
      return 'Un pôle avec ce libellé existe déjà.'
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
