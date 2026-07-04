import { describe, expect, it } from 'vitest'

import { shouldShowSignalCreateActionPlan } from '@/features/signals/lib/signal-create-action'

import {
  canCreateExecutionFeedActionPlan,
  canCreateSignalLinkedActionPlan,
  canCreateSignalLinkedActionPlanFromSignalHints,
} from './action-plan-management-access'

describe('canCreateExecutionFeedActionPlan', () => {
  it('returns true when can_create_action hint is true', () => {
    expect(canCreateExecutionFeedActionPlan(true)).toBe(true)
  })

  it('returns false when can_create_action hint is false', () => {
    expect(canCreateExecutionFeedActionPlan(false)).toBe(false)
  })
})

describe('canCreateSignalLinkedActionPlan', () => {
  it('allows manager when can_create_action is true', () => {
    expect(canCreateSignalLinkedActionPlan({ role: 'manager', canCreateAction: true })).toBe(true)
  })

  it('allows director and owner when can_create_action is true', () => {
    expect(canCreateSignalLinkedActionPlan({ role: 'director', canCreateAction: true })).toBe(true)
    expect(canCreateSignalLinkedActionPlan({ role: 'owner', canCreateAction: true })).toBe(true)
  })

  it('denies staff even when can_create_action is true', () => {
    expect(canCreateSignalLinkedActionPlan({ role: 'staff', canCreateAction: true })).toBe(false)
  })

  it('denies manager when can_create_action is false', () => {
    expect(canCreateSignalLinkedActionPlan({ role: 'manager', canCreateAction: false })).toBe(false)
  })
})

describe('canCreateSignalLinkedActionPlanFromSignalHints', () => {
  it('delegates to shouldShowSignalCreateActionPlan', () => {
    const hints = { can_create_action: true }
    expect(canCreateSignalLinkedActionPlanFromSignalHints(hints)).toBe(
      shouldShowSignalCreateActionPlan(hints),
    )
  })

  it('returns false when hint is absent', () => {
    expect(canCreateSignalLinkedActionPlanFromSignalHints({})).toBe(false)
    expect(canCreateSignalLinkedActionPlanFromSignalHints(null)).toBe(false)
  })
})
