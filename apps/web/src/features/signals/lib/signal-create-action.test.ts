import { describe, expect, it } from 'vitest'

import { shouldShowSignalCreateActionPlan } from './signal-create-action'

describe('shouldShowSignalCreateActionPlan', () => {
  it('returns true when can_create_action is true', () => {
    expect(shouldShowSignalCreateActionPlan({ can_create_action: true })).toBe(true)
  })

  it('returns false when can_create_action is false', () => {
    expect(shouldShowSignalCreateActionPlan({ can_create_action: false })).toBe(false)
  })

  it('returns false for staff signal hints even when bootstrap allows free create', () => {
    expect(shouldShowSignalCreateActionPlan({ can_create_action: false })).toBe(false)
  })

  it('returns false when hints are absent or indeterminate', () => {
    expect(shouldShowSignalCreateActionPlan({})).toBe(false)
    expect(shouldShowSignalCreateActionPlan({ can_create_action: undefined })).toBe(false)
    expect(shouldShowSignalCreateActionPlan(null)).toBe(false)
    expect(shouldShowSignalCreateActionPlan(undefined)).toBe(false)
  })
})
