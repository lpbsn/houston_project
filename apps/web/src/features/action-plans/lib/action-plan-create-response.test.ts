import { describe, expect, it } from 'vitest'

import {
  isActionPlanExecutionDetail,
  isActionPlanPlanningSubmitResponse,
  resolveDirectCreateSuccessPath,
  resolvePlanningSuccessPath,
} from '@/features/action-plans/lib/action-plan-create-response'
import type { ActionPlanPlanningSubmitResponse } from '@/features/action-plans/types'
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

function planningResponse(
  partial: Partial<ActionPlanPlanningSubmitResponse>,
): ActionPlanPlanningSubmitResponse {
  return {
    replayed: false,
    action_plan_id: 'plan-1',
    summary: { executions_created: 0, schedules_created: 0 },
    executions: [],
    schedules: [],
    ...partial,
  }
}

describe('resolvePlanningSuccessPath', () => {
  it('opens the execution when the launch created exactly one and no schedule', () => {
    expect(
      resolvePlanningSuccessPath(
        planningResponse({
          summary: { executions_created: 1, schedules_created: 0 },
          executions: [
            { item_id: 'i1', id: 'exec-1', primary_membership_id: null, status: 'in_progress' },
          ],
        }),
      ),
    ).toBe('/action-plans/executions/exec-1')
  })

  it('stays on the execution feed when a schedule or several executions were created', () => {
    expect(
      resolvePlanningSuccessPath(
        planningResponse({
          summary: { executions_created: 0, schedules_created: 1 },
          schedules: [{ item_id: 'i1', id: 'sched-1', primary_membership_id: null, status: 'active' }],
        }),
      ),
    ).toBe('/execution')
    expect(
      resolvePlanningSuccessPath(
        planningResponse({
          summary: { executions_created: 2, schedules_created: 0 },
          executions: [
            { item_id: 'i1', id: 'exec-1', primary_membership_id: null, status: 'in_progress' },
            { item_id: 'i2', id: 'exec-2', primary_membership_id: null, status: 'in_progress' },
          ],
        }),
      ),
    ).toBe('/execution')
    expect(resolvePlanningSuccessPath(planningResponse({}))).toBe('/execution')
  })
})

describe('resolveDirectCreateSuccessPath', () => {
  it('opens one execution and keeps a schedule or a template on the feed', () => {
    expect(
      resolveDirectCreateSuccessPath({
        id: 'exec-1',
        action_plan_id: 'plan-1',
        status: 'in_progress',
      } as ActionPlanExecutionDetail),
    ).toBe('/action-plans/executions/exec-1')
    expect(
      resolveDirectCreateSuccessPath(
        planningResponse({
          summary: { executions_created: 1, schedules_created: 0 },
          executions: [
            { item_id: 'i1', id: 'exec-9', primary_membership_id: null, status: 'scheduled' },
          ],
        }),
      ),
    ).toBe('/action-plans/executions/exec-9')
    expect(
      resolveDirectCreateSuccessPath(
        planningResponse({
          summary: { executions_created: 0, schedules_created: 1 },
          schedules: [{ item_id: 'i1', id: 'sched-1', primary_membership_id: null, status: 'active' }],
        }),
      ),
    ).toBe('/execution')
    expect(
      resolveDirectCreateSuccessPath({
        id: 'plan-1',
        title: 'Plan',
        is_reusable: true,
        tasks: [],
      } as ActionPlanDetail),
    ).toBe('/execution')
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
