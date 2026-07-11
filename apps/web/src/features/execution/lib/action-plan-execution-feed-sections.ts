import type { TerrainSectionDotVariant } from '@/lib/terrain-styles'

import type { ActionPlanExecutionFeedItem } from '@/features/action-plans/types'

export type ActionPlanExecutionFeedSectionKey =
  | 'pending_validation'
  | 'in_progress'
  | 'done'
  | 'canceled'

export type ActionPlanExecutionFeedSectionGroup = {
  section: ActionPlanExecutionFeedSectionKey
  label: string
  dotVariant: TerrainSectionDotVariant
  items: ActionPlanExecutionFeedItem[]
}

const SECTION_ORDER: ActionPlanExecutionFeedSectionKey[] = [
  'pending_validation',
  'in_progress',
  'done',
  'canceled',
]

const SECTION_META: Record<
  ActionPlanExecutionFeedSectionKey,
  { label: string; dotVariant: TerrainSectionDotVariant }
> = {
  pending_validation: { label: 'À valider', dotVariant: 'warning' },
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
      return 'in_progress'
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

export function groupActionPlanExecutionsBySection(
  items: ActionPlanExecutionFeedItem[],
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
    const sectionItems = buckets.get(section)
    if (!sectionItems || sectionItems.length === 0) {
      return []
    }
    return [
      {
        section,
        ...SECTION_META[section],
        items: sectionItems,
      },
    ]
  })
}
