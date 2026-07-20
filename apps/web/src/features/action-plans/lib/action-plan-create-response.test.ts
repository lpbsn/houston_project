import { describe, expect, it } from 'vitest'

import {
  isActionPlanExecutionDetail,
  isActionPlanPlanningSubmitResponse,
} from '@/features/action-plans/lib/action-plan-create-response'
import type {
  ActionPlanCreate201Response,
  ActionPlanDetail,
  ActionPlanExecutionDetail,
} from '@/features/action-plans/types'

describe('isActionPlanExecutionDetail', () => {
  it('returns true when status and action_plan_id keys are present', () => {
    const execution = {
      id: 'exec-1',
      action_plan_id: null,
      status: 'in_progress',
      title: 'Plan',
    } as ActionPlanExecutionDetail

    expect(isActionPlanExecutionDetail(execution)).toBe(true)
  })

  it('returns false for catalog template detail', () => {
    const template = {
      id: 'plan-1',
      title: 'Plan',
      tasks: [],
      is_reusable: true,
    } as ActionPlanDetail

    expect(isActionPlanExecutionDetail(template as ActionPlanCreate201Response)).toBe(false)
  })

  it('returns false for atomic planning create response', () => {
    expect(
      isActionPlanExecutionDetail({
        replayed: false,
        action_plan_id: 'plan-1',
        summary: { executions_created: 1, schedules_created: 0 },
        executions: [],
        schedules: [],
      } as ActionPlanCreate201Response),
    ).toBe(false)
  })
})

describe('isActionPlanPlanningSubmitResponse', () => {
  it('returns true for planning submit / atomic create shape', () => {
    expect(
      isActionPlanPlanningSubmitResponse({
        replayed: false,
        action_plan_id: 'plan-1',
        summary: { executions_created: 1, schedules_created: 1 },
        executions: [{ item_id: 'i1', id: 'e1', primary_membership_id: null, status: 'scheduled' }],
        schedules: [],
      }),
    ).toBe(true)
  })

  it('returns false for execution detail', () => {
    expect(
      isActionPlanPlanningSubmitResponse({
        id: 'exec-1',
        action_plan_id: 'plan-1',
        status: 'in_progress',
      }),
    ).toBe(false)
  })
})
