function getAuthErrorParts(error: unknown): { code: string | null; message: string | null } {
  if (typeof error !== 'object' || !error) {
    return { code: null, message: null }
  }

  const record = error as { code?: unknown; message?: unknown; name?: unknown }
  const code = typeof record.code === 'string' ? record.code : null
  const message = typeof record.message === 'string' ? record.message : null
  return { code, message }
}

export function mapInvitationErrorMessage(
  code: string | null | undefined,
  fallbackDetail?: string | null,
): string {
  switch (code) {
    case 'membership_invitation_user_exists':
      return 'Un compte Houston existe déjà pour cet email. L’invitation par email n’est pas possible.'
    case 'membership_invitation_duplicate':
      return 'Cet utilisateur est déjà associé à l’établissement ou dispose déjà d’une invitation.'
    case 'membership_invitation_owner_conflict':
      return 'Cette invitation est en conflit avec une membership existante qui n’est pas propriétaire.'
    case 'organizational_owner_invariant_conflict':
      return 'La couverture des propriétaires de l’organisation est incohérente. Réessayez plus tard ou contactez le support.'
    case 'membership_invitation_role_not_allowed':
      return 'Ce rôle ne peut pas être invité avec votre profil actuel.'
    case 'membership_invitation_invalid':
      return fallbackDetail?.trim() || 'Cette invitation n’est pas valide.'
    default:
      return fallbackDetail?.trim() || 'L’invitation n’a pas pu être créée.'
  }
}

export function resolveInvitationErrorMessage(error: unknown, fallback: string): string {
  const { code, message } = getAuthErrorParts(error)
  if (code || message) {
    return mapInvitationErrorMessage(code, message)
  }

  return fallback
}
