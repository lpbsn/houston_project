import type { TerrainSectionDotVariant } from '@/lib/terrain-styles'

import type { ActionFeedItem } from '@/features/actions/types'

export type ExecutionActionSectionKey =
  | 'pending_validation'
  | 'todo'
  | 'in_progress'
  | 'done'
  | 'canceled'

export type ExecutionActionSectionGroup = {
  section: ExecutionActionSectionKey
  label: string
  dotVariant: TerrainSectionDotVariant
  items: ActionFeedItem[]
}

const SECTION_ORDER: ExecutionActionSectionKey[] = [
  'pending_validation',
  'todo',
  'in_progress',
  'done',
  'canceled',
]

const SECTION_META: Record<
  ExecutionActionSectionKey,
  { label: string; dotVariant: TerrainSectionDotVariant }
> = {
  pending_validation: { label: 'À valider', dotVariant: 'warning' },
  todo: { label: 'À faire', dotVariant: 'warning' },
  in_progress: { label: 'En cours', dotVariant: 'primary' },
  done: { label: 'Terminées', dotVariant: 'success' },
  canceled: { label: 'Annulées', dotVariant: 'muted' },
}

export function getExecutionActionSection(
  action: ActionFeedItem,
): ExecutionActionSectionKey | null {
  switch (action.status) {
    case 'open':
    case 'reopened':
      return 'todo'
    case 'in_progress':
      return 'in_progress'
    case 'pending_validation':
      return 'pending_validation'
    case 'done':
      return 'done'
    case 'canceled':
      return 'canceled'
    default:
      return null
  }
}

/**
 * Groups execution feed actions by operational section. Preserves API order within each group.
 * Omits empty sections. Always returns section headers when at least one mappable action exists.
 */
export function groupExecutionActionsBySection(
  actions: ActionFeedItem[],
): ExecutionActionSectionGroup[] {
  const buckets = new Map<ExecutionActionSectionKey, ActionFeedItem[]>()

  for (const action of actions) {
    const section = getExecutionActionSection(action)
    if (!section) {
      continue
    }
    const bucket = buckets.get(section)
    if (bucket) {
      bucket.push(action)
    } else {
      buckets.set(section, [action])
    }
  }

  return SECTION_ORDER.flatMap((section) => {
    const items = buckets.get(section)
    if (!items || items.length === 0) {
      return []
    }
    return [
      {
        section,
        ...SECTION_META[section],
        items,
      },
    ]
  })
}
