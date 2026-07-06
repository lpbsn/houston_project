import { describe, expect, it } from 'vitest'

import type { ActionPlanExecutionFeedItem } from '@/features/action-plans/types'

import {
  getActionPlanExecutionFeedSection,
  groupActionPlanExecutionsBySection,
} from './action-plan-execution-feed-sections'

function buildFeedItem(
  overrides: Partial<ActionPlanExecutionFeedItem> & Pick<ActionPlanExecutionFeedItem, 'id' | 'status'>,
): ActionPlanExecutionFeedItem {
  return {
    title: 'Plan',
    description_short: 'Description',
    requires_validation: false,
    pilot_business_unit: { id: 'bu-1', key: 'restaurant', label: 'Restaurant' },
    involved_poles: [],
    signal_summary: null,
    assignees: [],
    end_at: null,
    is_overdue: false,
    task_count: 0,
    treated_task_count: 0,
    task_executions: [],
    last_activity_at: '2026-06-13T12:00:00Z',
    created_at: '2026-06-13T12:00:00Z',
    permission_hints: {
      can_mark_done: true,
      can_validate: false,
      can_reopen: false,
      can_cancel: false,
      is_pilot_pole_assignee: true,
    },
    ...overrides,
  }
}

describe('getActionPlanExecutionFeedSection', () => {
  it('maps pending_validation and in_progress statuses', () => {
    expect(getActionPlanExecutionFeedSection(buildFeedItem({ id: '1', status: 'pending_validation' }))).toBe(
      'pending_validation',
    )
    expect(getActionPlanExecutionFeedSection(buildFeedItem({ id: '2', status: 'in_progress' }))).toBe(
      'in_progress',
    )
  })

  it('returns null for unknown status', () => {
    expect(getActionPlanExecutionFeedSection(buildFeedItem({ id: '3', status: 'unknown' }))).toBeNull()
  })
})

describe('groupActionPlanExecutionsBySection', () => {
  it('orders pending_validation before in_progress and omits empty sections', () => {
    const inProgress = buildFeedItem({ id: 'in-progress', status: 'in_progress', title: 'En cours' })
    const pending = buildFeedItem({
      id: 'pending',
      status: 'pending_validation',
      title: 'À valider',
    })
    const unknown = buildFeedItem({ id: 'unknown', status: 'draft', title: 'Ignoré' })

    const groups = groupActionPlanExecutionsBySection([inProgress, pending, unknown])

    expect(groups.map((group) => group.section)).toEqual(['pending_validation', 'in_progress'])
    expect(groups[0]?.items.map((item) => item.id)).toEqual(['pending'])
    expect(groups[1]?.items.map((item) => item.id)).toEqual(['in-progress'])
  })
})
