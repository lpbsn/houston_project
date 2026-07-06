import { describe, expect, it } from 'vitest'

import { formatActionPlanFeedTaskProgressLabel } from './action-plan-execution-feed-card-display'

describe('formatActionPlanFeedTaskProgressLabel', () => {
  it('returns null when there are no tasks', () => {
    expect(formatActionPlanFeedTaskProgressLabel({ task_count: 0, treated_task_count: 0 })).toBeNull()
  })

  it('formats treated and total counts', () => {
    expect(formatActionPlanFeedTaskProgressLabel({ task_count: 4, treated_task_count: 1 })).toBe(
      'Tâches 1/4',
    )
  })
})
