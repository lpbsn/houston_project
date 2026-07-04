import { describe, expect, it } from 'vitest'

import {
  canShowActionPlanExecutionCancel,
  canShowActionPlanTaskMarkDone,
} from '@/features/action-plans/lib/action-plan-permission-hints'
import type { ActionPlanTaskExecution } from '@/features/action-plans/types'

describe('action-plan permission hints', () => {
  it('shows cancel only when allowed and not terminal', () => {
    expect(
      canShowActionPlanExecutionCancel(
        { can_mark_done: false, can_validate: false, can_reopen: false, can_cancel: true, is_pilot_pole_assignee: false },
        { isTerminal: false },
      ),
    ).toBe(true)
    expect(
      canShowActionPlanExecutionCancel(
        { can_mark_done: false, can_validate: false, can_reopen: false, can_cancel: true, is_pilot_pole_assignee: false },
        { isTerminal: true },
      ),
    ).toBe(false)
  })

  it('shows task mark done only for pending tasks', () => {
    const pendingTask = {
      id: 't1',
      status: 'pending',
      permission_hints: { can_mark_done: true, can_skip: true, can_create_observation: true },
    } as ActionPlanTaskExecution

    expect(
      canShowActionPlanTaskMarkDone(pendingTask.permission_hints, {
        isTerminal: false,
        task: pendingTask,
      }),
    ).toBe(true)
  })
})
