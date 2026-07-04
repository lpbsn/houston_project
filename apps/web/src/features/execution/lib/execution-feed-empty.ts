import type { ExecutionViewMode } from '@/features/actions/types'

export function getEmptyFeedDescription(viewMode: ExecutionViewMode): string {
  if (viewMode === 'personal') {
    return 'Aucune action, checklist ni plan d’action ne vous est assigné pour le moment.'
  }
  return 'Aucune action, checklist ni plan d’action visible dans votre périmètre pour le moment.'
}
