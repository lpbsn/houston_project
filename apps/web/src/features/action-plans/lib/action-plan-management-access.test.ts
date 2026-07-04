import { describe, expect, it } from 'vitest'

import { canCreateExecutionFeedActionPlan } from './action-plan-management-access'

describe('canCreateExecutionFeedActionPlan', () => {
  it('returns true when can_create_action hint is true', () => {
    expect(canCreateExecutionFeedActionPlan(true)).toBe(true)
  })

  it('returns false when can_create_action hint is false', () => {
    expect(canCreateExecutionFeedActionPlan(false)).toBe(false)
  })
})
