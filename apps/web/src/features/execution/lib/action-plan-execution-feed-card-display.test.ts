import { describe, expect, it } from 'vitest'

import {
  formatActionPlanFeedMetaParts,
  formatActionPlanFeedTaskProgressLabel,
} from './action-plan-execution-feed-card-display'

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
