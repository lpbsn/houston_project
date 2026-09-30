import type { TerrainSectionDotVariant } from '@/lib/terrain-styles'

import type { ActionPlanExecutionFeedCategory } from '@/features/action-plans/api'
import type {
  ActionPlanExecutionFeedItem,
  ActionPlanExecutionFeedSectionCounts,
} from '@/features/action-plans/types'

/** UI section keys for the shared feed grouping (overdue is not a business status). */
export type ActionPlanExecutionFeedSectionKey =
  | 'pending_validation'
  | 'overdue'
  | 'in_progress'

export type ActionPlanExecutionFeedSectionGroup = {
  section: ActionPlanExecutionFeedSectionKey
  label: string
  dotVariant: TerrainSectionDotVariant
  items: ActionPlanExecutionFeedItem[]
}

export const EXECUTION_FEED_PINNED_SECTION_KEY = 'pinned' as const

export const EXECUTION_FEED_DEFAULT_COLLAPSED_SECTIONS = [] as const

const SECTION_ORDER: ActionPlanExecutionFeedSectionKey[] = [
  'pending_validation',
  'overdue',
  'in_progress',
]

const SECTION_META: Record<
  ActionPlanExecutionFeedSectionKey,
  { label: string; dotVariant: TerrainSectionDotVariant }
> = {
  pending_validation: { label: 'À valider', dotVariant: 'warning' },
  overdue: { label: 'En retard', dotVariant: 'warning' },
  in_progress: { label: 'En cours', dotVariant: 'teal' },
}

export const EXECUTION_FEED_CATEGORY_LABELS: Record<ActionPlanExecutionFeedCategory, string> = {
  all: 'Tout',
  pending_validation: 'À valider',
  overdue: 'En retard',
  in_progress: 'En cours',
}

export function retainedTerminalExecutionItems(
  items: ActionPlanExecutionFeedItem[],
  category: ActionPlanExecutionFeedCategory = 'all',
): ActionPlanExecutionFeedItem[] {
  if (category !== 'all') {
    return []
  }
  return items.filter((item) => item.status === 'done' || item.status === 'canceled')
}

export function getActionPlanExecutionFeedSection(
  item: ActionPlanExecutionFeedItem,
): ActionPlanExecutionFeedSectionKey | null {
  switch (item.status) {
    case 'pending_validation':
      return 'pending_validation'
    case 'in_progress':
      return item.is_overdue ? 'overdue' : 'in_progress'
    default:
      return null
  }
}

/**
 * Builds separators only for categories represented by loaded L items.
 * Counts describe the complete authorized selection and never hide received items.
 */
export function groupActionPlanExecutionsBySection(
  items: ActionPlanExecutionFeedItem[],
  _sectionCounts: Pick<ActionPlanExecutionFeedSectionCounts, ActionPlanExecutionFeedSectionKey>,
  category: ActionPlanExecutionFeedCategory = 'all',
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

  const sections =
    category === 'all' ? SECTION_ORDER : SECTION_ORDER.filter((section) => section === category)
  return sections.flatMap((section) => {
    const loadedItems = buckets.get(section) ?? []
    if (loadedItems.length === 0) {
      return []
    }
    return [
      {
        section,
        ...SECTION_META[section],
        items: loadedItems,
      },
    ]
  })
}
