import { describe, expect, it } from 'vitest'

import { isActionPlanExecutionDetail } from '@/features/action-plans/lib/action-plan-create-response'
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
})
