function getAuthErrorParts(error: unknown): { code: string | null; message: string | null } {
  if (typeof error !== 'object' || !error) {
    return { code: null, message: null }
  }

  const record = error as { code?: unknown; message?: unknown }
  const code = typeof record.code === 'string' ? record.code : null
  const message = typeof record.message === 'string' ? record.message : null
  return { code, message }
}

export function mapMembershipManagementErrorMessage(
  code: string | null | undefined,
  fallbackDetail?: string | null,
): string {
  switch (code) {
    case 'membership_role_change_forbidden':
      return 'Ce changement de rôle n’est pas autorisé.'
    case 'organizational_owner_invariant_conflict':
      return 'La couverture des propriétaires de l’organisation est incohérente. L’opération a été annulée.'
    case 'membership_management_forbidden':
      return 'Vous ne pouvez pas gérer cette membership.'
    case 'invited_membership_activation_forbidden':
      return 'Une membership invitée ne peut pas être activée ainsi. Le membre doit d’abord accepter l’invitation.'
    default:
      return fallbackDetail?.trim() || 'La membership n’a pas pu être mise à jour.'
  }
}

export function resolveMembershipManagementErrorMessage(error: unknown, fallback: string): string {
  const { code, message } = getAuthErrorParts(error)

  if (
    typeof message === 'string' &&
    message.toLowerCase().includes('last active owner')
  ) {
    return 'Vous ne pouvez pas désactiver le dernier propriétaire actif de l’organisation.'
  }

  if (code || message) {
    return mapMembershipManagementErrorMessage(code, message)
  }

  return fallback
}
