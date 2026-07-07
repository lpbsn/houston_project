import { describe, expect, it } from 'vitest'

import {
  canOpenActionPlanExecutionFeedCardActions,
  getActionPlanExecutionFeedCardActionOptions,
} from './action-plan-execution-feed-card-actions'

function hints(overrides: Partial<{ can_pin: boolean }> = {}) {
  return {
    can_mark_done: true,
    can_validate: false,
    can_reopen: false,
    can_cancel: false,
    is_pilot_pole_assignee: true,
    can_pin: false,
    ...overrides,
  }
}

describe('canOpenActionPlanExecutionFeedCardActions', () => {
  it('returns false when can_pin is false', () => {
    expect(canOpenActionPlanExecutionFeedCardActions(hints())).toBe(false)
  })

  it('returns true when can_pin is true', () => {
    expect(canOpenActionPlanExecutionFeedCardActions(hints({ can_pin: true }))).toBe(true)
  })
})

describe('getActionPlanExecutionFeedCardActionOptions', () => {
  it('returns empty list when can_pin is false', () => {
    expect(
      getActionPlanExecutionFeedCardActionOptions({
        permission_hints: hints(),
        is_pinned: false,
      }),
    ).toEqual([])
  })

  it('returns Épingler when not pinned', () => {
    expect(
      getActionPlanExecutionFeedCardActionOptions({
        permission_hints: hints({ can_pin: true }),
        is_pinned: false,
      }),
    ).toEqual([{ id: 'pin', label: 'Épingler' }])
  })

  it('returns Désépingler when pinned', () => {
    expect(
      getActionPlanExecutionFeedCardActionOptions({
        permission_hints: hints({ can_pin: true }),
        is_pinned: true,
      }),
    ).toEqual([{ id: 'pin', label: 'Désépingler' }])
  })
})
