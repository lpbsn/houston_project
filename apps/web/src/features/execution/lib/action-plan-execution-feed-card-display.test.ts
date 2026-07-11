import { describe, expect, it } from 'vitest'

import {
  formatActionPlanFeedMetaParts,
  formatActionPlanFeedTaskProgressLabel,
  getActionPlanFeedProgressState,
  getActionPlanFeedSidebarState,
} from './action-plan-execution-feed-card-display'

const NOW = Date.parse('2026-07-10T12:00:00Z')

describe('getActionPlanFeedSidebarState', () => {
  it('returns countdown in hours when end_at is within 24 hours', () => {
    expect(getActionPlanFeedSidebarState('2026-07-10T16:00:00Z', NOW)).toEqual({
      variant: 'countdown',
      prefix: 'DANS',
      value: '4h',
    })
  })

  it('returns countdown in days when end_at is at least 24 hours away', () => {
    expect(getActionPlanFeedSidebarState('2026-07-13T12:00:00Z', NOW)).toEqual({
      variant: 'countdown',
      prefix: 'DANS',
      value: '3j',
    })
  })

  it('returns no_deadline when end_at is absent', () => {
    expect(getActionPlanFeedSidebarState(null, NOW)).toEqual({
      variant: 'no_deadline',
    })
  })

  it('returns no_deadline when end_at is invalid', () => {
    expect(getActionPlanFeedSidebarState('not-a-date', NOW)).toEqual({
      variant: 'no_deadline',
    })
  })

  it('returns overdue when end_at is in the past', () => {
    expect(getActionPlanFeedSidebarState('2026-07-10T11:00:00Z', NOW)).toEqual({
      variant: 'overdue',
    })
  })

  it('uses a minimum of 1 hour for sub-day remaining time', () => {
    expect(getActionPlanFeedSidebarState('2026-07-10T12:15:00Z', NOW)).toEqual({
      variant: 'countdown',
      prefix: 'DANS',
      value: '1h',
    })
  })
})

describe('getActionPlanFeedProgressState', () => {
  it('returns clamped progress state', () => {
    expect(getActionPlanFeedProgressState({ task_count: 5, treated_task_count: 2 })).toEqual({
      total: 5,
      filled: 2,
      fractionLabel: '2/5',
    })
  })

  it('clamps filled when treated_task_count exceeds task_count', () => {
    expect(getActionPlanFeedProgressState({ task_count: 4, treated_task_count: 9 })).toEqual({
      total: 4,
      filled: 4,
      fractionLabel: '4/4',
    })
  })

  it('clamps negative values to zero', () => {
    expect(getActionPlanFeedProgressState({ task_count: -2, treated_task_count: -1 })).toBeNull()
    expect(getActionPlanFeedProgressState({ task_count: 3, treated_task_count: -1 })).toEqual({
      total: 3,
      filled: 0,
      fractionLabel: '0/3',
    })
  })

  it('returns null when task_count is zero', () => {
    expect(getActionPlanFeedProgressState({ task_count: 0, treated_task_count: 0 })).toBeNull()
  })
})

describe('formatActionPlanFeedTaskProgressLabel', () => {
  it('returns null when there are no tasks', () => {
    expect(formatActionPlanFeedTaskProgressLabel({ task_count: 0, treated_task_count: 0 })).toBeNull()
  })

  it('formats treated and total counts', () => {
    expect(formatActionPlanFeedTaskProgressLabel({ task_count: 4, treated_task_count: 1 })).toBe(
      'Tâche 1/4',
    )
  })
})

describe('formatActionPlanFeedMetaParts', () => {
  it('returns both labels when end_at and tasks are present', () => {
    const parts = formatActionPlanFeedMetaParts({
      end_at: '2026-07-06T18:30:00Z',
      task_count: 4,
      treated_task_count: 1,
    })

    expect(parts.deadlineLabel).toMatch(/^Échéance : /)
    expect(parts.taskProgressLabel).toBe('Tâche 1/4')
  })

  it('returns deadline only when task_count is zero', () => {
    const parts = formatActionPlanFeedMetaParts({
      end_at: '2026-07-06T18:30:00Z',
      task_count: 0,
      treated_task_count: 0,
    })

    expect(parts.deadlineLabel).toMatch(/^Échéance : /)
    expect(parts.taskProgressLabel).toBeNull()
  })

  it('returns task progress only when end_at is null', () => {
    const parts = formatActionPlanFeedMetaParts({
      end_at: null,
      task_count: 4,
      treated_task_count: 0,
    })

    expect(parts.deadlineLabel).toBeNull()
    expect(parts.taskProgressLabel).toBe('Tâche 0/4')
  })

  it('returns null labels when neither end_at nor tasks are present', () => {
    const parts = formatActionPlanFeedMetaParts({
      end_at: null,
      task_count: 0,
      treated_task_count: 0,
    })

    expect(parts.deadlineLabel).toBeNull()
    expect(parts.taskProgressLabel).toBeNull()
  })
})
