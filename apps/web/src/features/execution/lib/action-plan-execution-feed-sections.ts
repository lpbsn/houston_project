import type { TerrainSectionDotVariant } from '@/lib/terrain-styles'

import type {
  ActionPlanExecutionFeedItem,
  ActionPlanExecutionFeedSectionCounts,
} from '@/features/action-plans/types'

/** UI section keys for the shared feed grouping (overdue is not a business status). */
export type ActionPlanExecutionFeedSectionKey =
  | 'pending_validation'
  | 'overdue'
  | 'in_progress'
  | 'done'
  | 'canceled'

export type ActionPlanExecutionFeedSectionGroup = {
  section: ActionPlanExecutionFeedSectionKey
  label: string
  dotVariant: TerrainSectionDotVariant
  items: ActionPlanExecutionFeedItem[]
}

export const EXECUTION_FEED_PINNED_SECTION_KEY = 'pinned' as const

export const EXECUTION_FEED_DEFAULT_COLLAPSED_SECTIONS = ['done', 'canceled'] as const

const SECTION_ORDER: ActionPlanExecutionFeedSectionKey[] = [
  'pending_validation',
  'overdue',
  'in_progress',
  'done',
  'canceled',
]

const SECTION_META: Record<
  ActionPlanExecutionFeedSectionKey,
  { label: string; dotVariant: TerrainSectionDotVariant }
> = {
  pending_validation: { label: 'À valider', dotVariant: 'warning' },
  overdue: { label: 'En retard', dotVariant: 'warning' },
  in_progress: { label: 'En cours', dotVariant: 'teal' },
  done: { label: 'Terminés', dotVariant: 'success' },
  canceled: { label: 'Annulés', dotVariant: 'muted' },
}

export function getActionPlanExecutionFeedSection(
  item: ActionPlanExecutionFeedItem,
): ActionPlanExecutionFeedSectionKey | null {
  switch (item.status) {
    case 'pending_validation':
      return 'pending_validation'
    case 'in_progress':
      return item.is_overdue ? 'overdue' : 'in_progress'
    case 'done':
      return 'done'
    case 'canceled':
      return 'canceled'
    default:
      return null
  }
}

export function partitionActionPlanExecutionFeedPinnedItems(
  items: ActionPlanExecutionFeedItem[],
): {
  pinnedItems: ActionPlanExecutionFeedItem[]
  unpinnedItems: ActionPlanExecutionFeedItem[]
} {
  const pinnedItems: ActionPlanExecutionFeedItem[] = []
  const unpinnedItems: ActionPlanExecutionFeedItem[] = []

  for (const item of items) {
    if (item.is_pinned) {
      pinnedItems.push(item)
    } else {
      unpinnedItems.push(item)
    }
  }

  return { pinnedItems, unpinnedItems }
}

/**
 * Builds feed section groups. Section presence is driven only by server
 * `section_counts` (> 0), not by how many matching items are already loaded.
 * Loaded items fill each section; empty `items` means “not yet paginated in”.
 */
export function groupActionPlanExecutionsBySection(
  items: ActionPlanExecutionFeedItem[],
  sectionCounts: Pick<ActionPlanExecutionFeedSectionCounts, ActionPlanExecutionFeedSectionKey>,
): ActionPlanExecutionFeedSectionGroup[] {
  const buckets = new Map<ActionPlanExecutionFeedSectionKey, ActionPlanExecutionFeedItem[]>()

  for (const item of items) {
    const section = getActionPlanExecutionFeedSection(item)
    if (!section) {
      continue
    }
    const bucket = buckets.get(section)
    if (bucket) {
      bucket.push(item)
    } else {
      buckets.set(section, [item])
    }
  }

  return SECTION_ORDER.flatMap((section) => {
    if (sectionCounts[section] <= 0) {
      return []
    }
    return [
      {
        section,
        ...SECTION_META[section],
        items: buckets.get(section) ?? [],
      },
    ]
  })
}

export function hasActionPlanExecutionFeedSections(
  sectionCounts: ActionPlanExecutionFeedSectionCounts,
): boolean {
  if (sectionCounts.pinned > 0) {
    return true
  }
  return SECTION_ORDER.some((section) => sectionCounts[section] > 0)
}
