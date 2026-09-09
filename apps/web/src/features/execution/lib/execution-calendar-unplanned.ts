import type { TerrainSectionDotVariant } from '@/lib/terrain-styles'
import type { ActionPlanExecutionFeedItem } from '@/features/action-plans/types'

export type CalendarUnplannedSectionHeader = {
  label: string
  count: number
  dotVariant: TerrainSectionDotVariant
}

export function calendarUnplannedSectionHeader(
  items: Array<Pick<ActionPlanExecutionFeedItem, 'status'>>,
): CalendarUnplannedSectionHeader {
  const count = items.length
  const pendingCount = items.filter((item) => item.status === 'pending_validation').length
  if (pendingCount > 0) {
    return {
      label: `Non planifiés · ${pendingCount} à valider`,
      count,
      dotVariant: 'warning',
    }
  }
  return {
    label: 'Non planifiés',
    count,
    dotVariant: 'muted',
  }
}
