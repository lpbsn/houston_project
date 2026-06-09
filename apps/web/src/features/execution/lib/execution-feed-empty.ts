import type { ExecutionViewMode } from '@/features/actions/types'

export function getEmptyFeedDescription(viewMode: ExecutionViewMode): string {
  if (viewMode === 'personal') {
    return 'Aucune action ni checklist ne vous est assignée pour le moment.'
  }
  return 'Aucune action ni checklist visible dans votre périmètre pour le moment.'
}
