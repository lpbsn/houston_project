import { describe, expect, it } from 'vitest'

import type { ExecutionFeedItem } from '@/features/actions/types'
import { buildActionFeedItem } from '@/features/actions/test-fixtures'

import { splitExecutionFeedItems } from './execution-feed-sections'

function makeAction(id: string, status: string) {
  return buildActionFeedItem({ id, status })
}

function makeChecklist(id: string, status: string) {
  return {
    id,
    title: 'Checklist',
    execution_source: 'template',
    status,
    end_at: null,
    is_overdue: false,
    business_unit_key: null,
    business_unit_label: null,
    assigned_to_display_name: 'Staff',
    last_activity_at: new Date().toISOString(),
    created_at: new Date().toISOString(),
    progress_treated_count: 0,
    progress_total_count: 2,
  }
}

describe('splitExecutionFeedItems', () => {
  it('separates checklist and action items', () => {
    const items: ExecutionFeedItem[] = [
      { item_type: 'action', action: makeAction('a1', 'open') },
      { item_type: 'checklist', checklist: makeChecklist('c1', 'assigned') },
      { item_type: 'checklist', checklist: makeChecklist('c2', 'in_progress') },
    ]

    const { checklistItems, actionItems } = splitExecutionFeedItems(items)

    expect(actionItems).toHaveLength(1)
    expect(actionItems[0]?.id).toBe('a1')
    expect(checklistItems).toHaveLength(2)
    expect(checklistItems.map((item) => item.id)).toEqual(['c1', 'c2'])
  })

  it('preserves API order within each list', () => {
    const items: ExecutionFeedItem[] = [
      { item_type: 'checklist', checklist: makeChecklist('c-first', 'assigned') },
      { item_type: 'action', action: makeAction('a-first', 'open') },
      { item_type: 'checklist', checklist: makeChecklist('c-second', 'in_progress') },
      { item_type: 'action', action: makeAction('a-second', 'in_progress') },
    ]

    const { checklistItems, actionItems } = splitExecutionFeedItems(items)

    expect(checklistItems.map((item) => item.id)).toEqual(['c-first', 'c-second'])
    expect(actionItems.map((item) => item.id)).toEqual(['a-first', 'a-second'])
  })

  it('ignores terminal checklist statuses', () => {
    const items: ExecutionFeedItem[] = [
      { item_type: 'checklist', checklist: makeChecklist('c-done', 'done') },
      { item_type: 'checklist', checklist: makeChecklist('c-cancel', 'canceled') },
    ]

    const { checklistItems, actionItems } = splitExecutionFeedItems(items)

    expect(checklistItems).toEqual([])
    expect(actionItems).toEqual([])
  })

  it('ignores actions with unknown status', () => {
    const items: ExecutionFeedItem[] = [
      { item_type: 'action', action: makeAction('a1', 'open') },
      { item_type: 'action', action: makeAction('a2', 'draft') },
    ]

    const { actionItems } = splitExecutionFeedItems(items)

    expect(actionItems.map((item) => item.id)).toEqual(['a1'])
  })

  it('returns empty lists when no mappable items exist', () => {
    expect(splitExecutionFeedItems([])).toEqual({ checklistItems: [], actionItems: [] })
  })
})
