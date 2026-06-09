import type { ActionFeedItem, ExecutionFeedItem } from '@/features/actions/types'
import type { ChecklistFeedItem } from '@/features/checklists/types'
import { getChecklistFeedSection } from '@/features/checklists/lib/checklist-display'

import { getExecutionActionSection } from './execution-action-sections'

export type SplitExecutionFeedItemsResult = {
  checklistItems: ChecklistFeedItem[]
  actionItems: ActionFeedItem[]
}

/**
 * Splits execution feed items into checklist and action lists.
 * Preserves API order within each list. Excludes terminal checklists and unmappable entries.
 */
export function splitExecutionFeedItems(items: ExecutionFeedItem[]): SplitExecutionFeedItemsResult {
  const checklistItems: ChecklistFeedItem[] = []
  const actionItems: ActionFeedItem[] = []

  for (const entry of items) {
    if (entry.item_type === 'checklist' && entry.checklist) {
      if (getChecklistFeedSection(entry.checklist) !== null) {
        checklistItems.push(entry.checklist)
      }
      continue
    }

    if (entry.item_type === 'action' && entry.action) {
      if (getExecutionActionSection(entry.action) !== null) {
        actionItems.push(entry.action)
      }
    }
  }

  return { checklistItems, actionItems }
}
