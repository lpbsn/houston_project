import { describe, expect, it } from 'vitest'

import { shouldShowSignalCreateActionPlan } from '@/features/signals/lib/signal-create-action'

import {
  canCreateExecutionFeedActionPlan,
  canCreateSignalLinkedActionPlan,
  canCreateSignalLinkedActionPlanFromSignalHints,
} from './action-plan-management-access'

describe('canCreateExecutionFeedActionPlan', () => {
  it('returns true when can_create_action_plan hint is true', () => {
    expect(canCreateExecutionFeedActionPlan(true)).toBe(true)
  })

  it('returns false when can_create_action_plan hint is false', () => {
    expect(canCreateExecutionFeedActionPlan(false)).toBe(false)
  })
})

describe('canCreateSignalLinkedActionPlan', () => {
  it('allows manager when can_create_action_plan is true', () => {
    expect(
      canCreateSignalLinkedActionPlan({ role: 'manager', canCreateActionPlan: true }),
    ).toBe(true)
  })

  it('allows director and owner when can_create_action_plan is true', () => {
    expect(
      canCreateSignalLinkedActionPlan({ role: 'director', canCreateActionPlan: true }),
    ).toBe(true)
    expect(canCreateSignalLinkedActionPlan({ role: 'owner', canCreateActionPlan: true })).toBe(true)
  })

  it('denies staff even when can_create_action_plan is true', () => {
    expect(canCreateSignalLinkedActionPlan({ role: 'staff', canCreateActionPlan: true })).toBe(
      false,
    )
  })

  it('denies manager when can_create_action_plan is false', () => {
    expect(
      canCreateSignalLinkedActionPlan({ role: 'manager', canCreateActionPlan: false }),
    ).toBe(false)
  })
})

describe('canCreateSignalLinkedActionPlanFromSignalHints', () => {
  it('delegates to shouldShowSignalCreateActionPlan', () => {
    const hints = { can_create_linked_action_plan: true }
    expect(canCreateSignalLinkedActionPlanFromSignalHints(hints)).toBe(
      shouldShowSignalCreateActionPlan(hints),
    )
  })

  it('returns false when hint is absent', () => {
    expect(canCreateSignalLinkedActionPlanFromSignalHints({})).toBe(false)
    expect(canCreateSignalLinkedActionPlanFromSignalHints(null)).toBe(false)
  })
})
