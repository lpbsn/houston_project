import { describe, expect, it } from 'vitest'

import type { ActionPlanExecutionFeedItem } from '@/features/action-plans/types'

import {
  getActionPlanExecutionFeedSection,
  groupActionPlanExecutionsBySection,
  mergeScheduledItemsIntoFeedSections,
  partitionActionPlanExecutionFeedPinnedItems,
} from './action-plan-execution-feed-sections'

function buildFeedItem(
  overrides: Partial<ActionPlanExecutionFeedItem> & Pick<ActionPlanExecutionFeedItem, 'id' | 'status'>,
): ActionPlanExecutionFeedItem {
  return {
    title: 'Plan',
    description_short: 'Description',
    requires_validation: false,
    pilot_business_unit: { id: 'bu-1', specific_name: 'Restaurant', instance_description: '', active: true, generic: { key: 'restaurant', label: 'Restaurant', description: '', unit_type: 'dedicated' } },
    involved_poles: [],
    signal_summary: null,
    assignees: [],
    start_at: null,
    end_at: null,
    is_overdue: false,
    task_count: 0,
    treated_task_count: 0,
    task_executions: [],
    last_activity_at: '2026-06-13T12:00:00Z',
    created_at: '2026-06-13T12:00:00Z',
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
  it('maps pending_validation and in_progress statuses', () => {
    expect(getActionPlanExecutionFeedSection(buildFeedItem({ id: '1', status: 'pending_validation' }))).toBe(
      'pending_validation',
    )
    expect(getActionPlanExecutionFeedSection(buildFeedItem({ id: '2', status: 'in_progress' }))).toBe(
      'in_progress',
    )
  })

  it('maps scheduled, done and canceled statuses', () => {
    expect(getActionPlanExecutionFeedSection(buildFeedItem({ id: 's', status: 'scheduled' }))).toBe(
      'scheduled',
    )
    expect(getActionPlanExecutionFeedSection(buildFeedItem({ id: '4', status: 'done' }))).toBe('done')
    expect(getActionPlanExecutionFeedSection(buildFeedItem({ id: '5', status: 'canceled' }))).toBe(
      'canceled',
    )
  })

  it('returns null for unknown status', () => {
    expect(getActionPlanExecutionFeedSection(buildFeedItem({ id: '3', status: 'unknown' }))).toBeNull()
  })
})

describe('groupActionPlanExecutionsBySection', () => {
  it('orders sections with scheduled after in_progress and before done', () => {
    const canceled = buildFeedItem({ id: 'canceled', status: 'canceled', title: 'Annulé' })
    const done = buildFeedItem({ id: 'done', status: 'done', title: 'Terminé' })
    const scheduled = buildFeedItem({ id: 'scheduled', status: 'scheduled', title: 'Planifiée' })
    const inProgress = buildFeedItem({ id: 'in-progress', status: 'in_progress', title: 'En cours' })
    const pending = buildFeedItem({
      id: 'pending',
      status: 'pending_validation',
      title: 'À valider',
    })

    const groups = groupActionPlanExecutionsBySection([
      canceled,
      done,
      scheduled,
      inProgress,
      pending,
    ])

    expect(groups.map((group) => group.section)).toEqual([
      'pending_validation',
      'in_progress',
      'scheduled',
      'done',
      'canceled',
    ])
    expect(groups.map((group) => group.label)).toEqual([
      'À valider',
      'En cours',
      'Planifiées',
      'Terminés',
      'Annulés',
    ])
    expect(groups.find((group) => group.section === 'scheduled')?.dotVariant).toBe('brown')
  })

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
    expect(groups[0]?.dotVariant).toBe('warning')
    expect(groups[1]?.dotVariant).toBe('teal')
    expect(groups[0]?.items.map((item) => item.id)).toEqual(['pending'])
    expect(groups[1]?.items.map((item) => item.id)).toEqual(['in-progress'])
  })
})

describe('mergeScheduledItemsIntoFeedSections', () => {
  it('inserts scheduled preview after in_progress and before done', () => {
    const groups = groupActionPlanExecutionsBySection([
      buildFeedItem({ id: 'in-progress', status: 'in_progress' }),
      buildFeedItem({ id: 'done', status: 'done' }),
    ])
    const scheduled = [buildFeedItem({ id: 'sched-1', status: 'scheduled' })]

    const merged = mergeScheduledItemsIntoFeedSections(groups, scheduled)

    expect(merged.map((group) => group.section)).toEqual(['in_progress', 'scheduled', 'done'])
    expect(merged[1]?.items.map((item) => item.id)).toEqual(['sched-1'])
  })

  it('places scheduled after pending_validation when in_progress is absent', () => {
    const groups = groupActionPlanExecutionsBySection([
      buildFeedItem({ id: 'pending', status: 'pending_validation' }),
      buildFeedItem({ id: 'done', status: 'done' }),
    ])
    const scheduled = [buildFeedItem({ id: 'sched-1', status: 'scheduled' })]

    const merged = mergeScheduledItemsIntoFeedSections(groups, scheduled)

    expect(merged.map((group) => group.section)).toEqual([
      'pending_validation',
      'scheduled',
      'done',
    ])
  })

  it('places scheduled after in_progress when both in_progress and pending exist', () => {
    const groups = groupActionPlanExecutionsBySection([
      buildFeedItem({ id: 'pending', status: 'pending_validation' }),
      buildFeedItem({ id: 'in-progress', status: 'in_progress' }),
    ])
    const scheduled = [buildFeedItem({ id: 'sched-1', status: 'scheduled' })]

    const merged = mergeScheduledItemsIntoFeedSections(groups, scheduled)

    expect(merged.map((group) => group.section)).toEqual([
      'pending_validation',
      'in_progress',
      'scheduled',
    ])
  })

  it('returns groups unchanged when scheduled preview is empty', () => {
    const groups = groupActionPlanExecutionsBySection([
      buildFeedItem({ id: 'in-progress', status: 'in_progress' }),
    ])

    expect(mergeScheduledItemsIntoFeedSections(groups, [])).toEqual(groups)
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
