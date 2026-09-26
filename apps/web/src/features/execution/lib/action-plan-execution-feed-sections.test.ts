import { describe, expect, it } from 'vitest'

import type { ActionPlanExecutionFeedItem } from '@/features/action-plans/types'

import {
  getActionPlanExecutionFeedSection,
  groupActionPlanExecutionsBySection,
  hasActionPlanExecutionFeedSections,
  partitionActionPlanExecutionFeedPinnedItems,
} from './action-plan-execution-feed-sections'

function buildFeedItem(
  overrides: Partial<ActionPlanExecutionFeedItem> & Pick<ActionPlanExecutionFeedItem, 'id' | 'status'>,
): ActionPlanExecutionFeedItem {
  return {
    title: 'Plan',
    description_short: 'Description',
    requires_validation: false,
    validated_at: null,
    validated_by_display_name: null,
    pilot_business_unit: {
      id: 'bu-1',
      specific_name: 'Restaurant',
      instance_description: '',
      active: true,
      generic: {
        key: 'restaurant',
        label: 'Restaurant',
        description: '',
        unit_type: 'dedicated',
      },
    },
    involved_poles: [],
    signal_summary: null,
    assignees: [],
    start_at: null,
    end_at: null,
    all_day: false,
    visible_from: null,
    is_overdue: false,
    task_count: 0,
    treated_task_count: 0,
    task_executions: [],
    last_activity_at: '2026-06-13T12:00:00Z',
    created_at: '2026-06-13T12:00:00Z',
    created_by_display_name: 'Alice Martin',
    marked_done_at: null,
    marked_done_by_display_name: null,
    canceled_at: null,
    active_review: null,
    is_pinned: false,
    permission_hints: {
      can_mark_done: true,
      can_validate: false,
      can_reopen: false,
      can_cancel: false,
      can_update: false,
      is_pilot_pole_assignee: true,
      can_pin: true,
    },
    ...overrides,
  }
}

describe('getActionPlanExecutionFeedSection', () => {
  it('maps pending_validation and splits in_progress by is_overdue', () => {
    expect(
      getActionPlanExecutionFeedSection(buildFeedItem({ id: '1', status: 'pending_validation' })),
    ).toBe('pending_validation')
    expect(
      getActionPlanExecutionFeedSection(
        buildFeedItem({ id: '2', status: 'in_progress', is_overdue: true }),
      ),
    ).toBe('overdue')
    expect(
      getActionPlanExecutionFeedSection(
        buildFeedItem({ id: '3', status: 'in_progress', is_overdue: false }),
      ),
    ).toBe('in_progress')
  })

  it('keeps overdue pending_validation in À valider', () => {
    expect(
      getActionPlanExecutionFeedSection(
        buildFeedItem({ id: 'p', status: 'pending_validation', is_overdue: true }),
      ),
    ).toBe('pending_validation')
  })

  it('maps done and canceled; ignores scheduled in item grouping', () => {
    expect(getActionPlanExecutionFeedSection(buildFeedItem({ id: '4', status: 'done' }))).toBe(
      'done',
    )
    expect(getActionPlanExecutionFeedSection(buildFeedItem({ id: '5', status: 'canceled' }))).toBe(
      'canceled',
    )
    expect(
      getActionPlanExecutionFeedSection(buildFeedItem({ id: 's', status: 'scheduled' })),
    ).toBeNull()
  })

  it('returns null for unknown status', () => {
    expect(getActionPlanExecutionFeedSection(buildFeedItem({ id: '3', status: 'unknown' }))).toBeNull()
  })
})

describe('groupActionPlanExecutionsBySection', () => {
  it('orders À valider → En retard → En cours → Terminés → Annulés', () => {
    const canceled = buildFeedItem({ id: 'canceled', status: 'canceled', title: 'Annulé' })
    const done = buildFeedItem({ id: 'done', status: 'done', title: 'Terminé' })
    const overdue = buildFeedItem({
      id: 'overdue',
      status: 'in_progress',
      is_overdue: true,
      title: 'Retard',
    })
    const inProgress = buildFeedItem({ id: 'in-progress', status: 'in_progress', title: 'En cours' })
    const pending = buildFeedItem({
      id: 'pending',
      status: 'pending_validation',
      title: 'À valider',
    })

    const groups = groupActionPlanExecutionsBySection(
      [canceled, done, inProgress, overdue, pending],
      {
        pending_validation: 1,
        overdue: 1,
        in_progress: 1,
        done: 1,
        canceled: 1,
      },
    )

    expect(groups.map((group) => group.section)).toEqual([
      'pending_validation',
      'overdue',
      'in_progress',
      'done',
      'canceled',
    ])
    expect(groups.map((group) => group.label)).toEqual([
      'À valider',
      'En retard',
      'En cours',
      'Terminés',
      'Annulés',
    ])
  })

  it('includes sections from section_counts even when items are not loaded yet', () => {
    const groups = groupActionPlanExecutionsBySection([], {
      pending_validation: 0,
      overdue: 2,
      in_progress: 1,
      done: 0,
      canceled: 0,
    })

    expect(groups.map((group) => group.section)).toEqual(['overdue', 'in_progress'])
    expect(groups[0]?.items).toEqual([])
    expect(groups[1]?.items).toEqual([])
  })

  it('omits zero-count sections and unknown statuses', () => {
    const inProgress = buildFeedItem({ id: 'in-progress', status: 'in_progress', title: 'En cours' })
    const pending = buildFeedItem({
      id: 'pending',
      status: 'pending_validation',
      title: 'À valider',
    })
    const unknown = buildFeedItem({ id: 'unknown', status: 'draft', title: 'Ignoré' })

    const groups = groupActionPlanExecutionsBySection([inProgress, pending, unknown], {
      pending_validation: 1,
      overdue: 0,
      in_progress: 1,
      done: 0,
      canceled: 0,
    })

    expect(groups.map((group) => group.section)).toEqual(['pending_validation', 'in_progress'])
    expect(groups[0]?.items.map((item) => item.id)).toEqual(['pending'])
    expect(groups[1]?.items.map((item) => item.id)).toEqual(['in-progress'])
  })
})

describe('hasActionPlanExecutionFeedSections', () => {
  it('is true when any section count is positive', () => {
    expect(
      hasActionPlanExecutionFeedSections({
        pinned: 0,
        pending_validation: 0,
        overdue: 0,
        in_progress: 0,
        done: 3,
        canceled: 0,
      }),
    ).toBe(true)
    expect(
      hasActionPlanExecutionFeedSections({
        pinned: 1,
        pending_validation: 0,
        overdue: 0,
        in_progress: 0,
        done: 0,
        canceled: 0,
      }),
    ).toBe(true)
  })

  it('is false when every section count is zero', () => {
    expect(
      hasActionPlanExecutionFeedSections({
        pinned: 0,
        pending_validation: 0,
        overdue: 0,
        in_progress: 0,
        done: 0,
        canceled: 0,
      }),
    ).toBe(false)
  })
})

describe('partitionActionPlanExecutionFeedPinnedItems', () => {
  it('splits pinned and unpinned items preserving order', () => {
    const pinned = buildFeedItem({ id: 'pinned', status: 'in_progress', is_pinned: true })
    const unpinned = buildFeedItem({ id: 'unpinned', status: 'pending_validation' })

    const { pinnedItems, unpinnedItems } = partitionActionPlanExecutionFeedPinnedItems([
      pinned,
      unpinned,
    ])

    expect(pinnedItems.map((item) => item.id)).toEqual(['pinned'])
    expect(unpinnedItems.map((item) => item.id)).toEqual(['unpinned'])
  })
})
