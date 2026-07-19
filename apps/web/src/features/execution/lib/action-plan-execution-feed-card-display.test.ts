import { describe, expect, it } from 'vitest'

import {
  formatActionPlanFeedMetaParts,
  formatActionPlanFeedStartCountdownValue,
  formatActionPlanFeedTaskProgressLabel,
  getActionPlanFeedProgressState,
  getActionPlanFeedSidebarState,
  getActionPlanFeedStartCountdownState,
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

  it.each([
    ['less than one hour', '2026-07-10T11:45:00Z', '1h'],
    ['several hours', '2026-07-10T08:00:00Z', '4h'],
    ['exactly 24 hours', '2026-07-09T12:00:00Z', '1j'],
    ['several days with remaining hours', '2026-07-07T04:00:00Z', '3j'],
  ])('returns overdue duration for %s', (_case, endAt, value) => {
    expect(getActionPlanFeedSidebarState(endAt, NOW, true)).toEqual({
      variant: 'overdue',
      prefix: 'RETARD',
      value,
    })
  })

  it.each([
    ['absent', null],
    ['invalid', 'not-a-date'],
    ['in the future', '2026-07-10T16:00:00Z'],
  ])('returns overdue 0h when end_at is %s', (_case, endAt) => {
    expect(getActionPlanFeedSidebarState(endAt, NOW, true)).toEqual({
      variant: 'overdue',
      prefix: 'RETARD',
      value: '0h',
    })
  })

  it('returns neutral 0h countdown when isOverdue is false and end_at is in the past', () => {
    expect(getActionPlanFeedSidebarState('2026-07-10T11:00:00Z', NOW, false)).toEqual({
      variant: 'countdown',
      prefix: 'DANS',
      value: '0h',
    })
  })

  it('uses a minimum of 1 hour for sub-day remaining time when isOverdue is false', () => {
    expect(getActionPlanFeedSidebarState('2026-07-10T12:15:00Z', NOW)).toEqual({
      variant: 'countdown',
      prefix: 'DANS',
      value: '1h',
    })
  })
})

describe('formatActionPlanFeedStartCountdownValue', () => {
  it.each([
    ['days', 3 * 24 * 60 * 60 * 1000, '3j'],
    ['hours', 7 * 60 * 60 * 1000, '7h'],
    ['under one hour', 30 * 60 * 1000, '<1h'],
    ['zero or past', 0, '<1h'],
    ['negative', -60_000, '<1h'],
  ])('formats %s remaining as %s', (_case, remainingMs, value) => {
    expect(formatActionPlanFeedStartCountdownValue(remainingMs)).toBe(value)
  })
})

describe('getActionPlanFeedStartCountdownState', () => {
  it('returns DÉBUT countdown from start_at', () => {
    expect(getActionPlanFeedStartCountdownState('2026-07-13T12:00:00Z', NOW)).toEqual({
      variant: 'start_countdown',
      prefix: 'DÉBUT',
      value: '3j',
    })
    expect(getActionPlanFeedStartCountdownState('2026-07-10T19:00:00Z', NOW)).toEqual({
      variant: 'start_countdown',
      prefix: 'DÉBUT',
      value: '7h',
    })
    expect(getActionPlanFeedStartCountdownState('2026-07-10T12:30:00Z', NOW)).toEqual({
      variant: 'start_countdown',
      prefix: 'DÉBUT',
      value: '<1h',
    })
  })

  it('returns no_start when start_at is absent or invalid', () => {
    expect(getActionPlanFeedStartCountdownState(null, NOW)).toEqual({ variant: 'no_start' })
    expect(getActionPlanFeedStartCountdownState(undefined, NOW)).toEqual({ variant: 'no_start' })
    expect(getActionPlanFeedStartCountdownState('not-a-date', NOW)).toEqual({ variant: 'no_start' })
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
