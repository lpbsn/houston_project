import type { ExecutionViewMode } from '@/features/execution/lib/types'

const ESTABLISHMENT_WIDE_EMPTY = 'Aucun plan d’action en cours dans l’établissement.'
const PERSONAL_ASSIGNED_EMPTY = 'Aucun plan d’action ne vous est assigné pour le moment.'

function isEstablishmentWideEmptyRole(role: string | null | undefined): boolean {
  return role === 'owner' || role === 'director'
}

export function getEmptyFeedDescription(
  viewMode: ExecutionViewMode,
  role?: string | null,
): string {
  if (viewMode === 'general' || isEstablishmentWideEmptyRole(role)) {
    return ESTABLISHMENT_WIDE_EMPTY
  }
  return PERSONAL_ASSIGNED_EMPTY
}
