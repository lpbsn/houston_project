import type { ExecutionViewMode } from '@/features/execution/lib/types'

export function getEmptyFeedDescription(viewMode: ExecutionViewMode): string {
  if (viewMode === 'personal') {
    return 'Aucun plan d’action ne vous est assigné pour le moment.'
  }
  return 'Aucun plan d’action en cours dans l’établissement.'
}
