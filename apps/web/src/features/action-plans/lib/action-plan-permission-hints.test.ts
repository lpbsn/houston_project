import { describe, expect, it } from 'vitest'

import {
  canShowActionPlanExecutionCancel,
  canShowActionPlanExecutionUpdate,
  canShowActionPlanTaskMarkDone,
  canShowActionPlanTaskUnmarkDone,
} from '@/features/action-plans/lib/action-plan-permission-hints'
import type { ActionPlanTaskExecution } from '@/features/action-plans/types'

describe('action-plan permission hints', () => {
  it('shows execution update only when can_update is true', () => {
    expect(
      canShowActionPlanExecutionUpdate({
        can_mark_done: false,
        can_validate: false,
        can_reopen: false,
        can_cancel: false,
        can_update: true,
        is_pilot_pole_assignee: false,
        can_pin: false,
      }),
    ).toBe(true)
    expect(
      canShowActionPlanExecutionUpdate({
        can_mark_done: false,
        can_validate: false,
        can_reopen: false,
        can_cancel: false,
        can_update: false,
        is_pilot_pole_assignee: false,
        can_pin: false,
      }),
    ).toBe(false)
  })

  it('shows cancel only when allowed and not terminal', () => {
    expect(
      canShowActionPlanExecutionCancel(
        {
          can_mark_done: false,
          can_validate: false,
          can_reopen: false,
          can_cancel: true,
          can_update: false,
          is_pilot_pole_assignee: false,
          can_pin: false,
        },
        { isTerminal: false },
      ),
    ).toBe(true)
    expect(
      canShowActionPlanExecutionCancel(
        {
          can_mark_done: false,
          can_validate: false,
          can_reopen: false,
          can_cancel: true,
          can_update: false,
          is_pilot_pole_assignee: false,
          can_pin: false,
        },
        { isTerminal: true },
      ),
    ).toBe(false)
  })

  it('shows task mark done only for pending tasks', () => {
    const pendingTask = {
      id: 't1',
      status: 'pending',
      permission_hints: { can_mark_done: true, can_unmark_done: false, can_skip: true, can_create_observation: true },
    } as ActionPlanTaskExecution

    expect(
      canShowActionPlanTaskMarkDone(pendingTask.permission_hints, {
        isTerminal: false,
        task: pendingTask,
      }),
    ).toBe(true)
  })

  it('shows task unmark done only for done tasks', () => {
    const doneTask = {
      id: 't1',
      status: 'done',
      permission_hints: {
        can_mark_done: false,
        can_unmark_done: true,
        can_skip: false,
        can_create_observation: false,
      },
    } as ActionPlanTaskExecution

    expect(
      canShowActionPlanTaskUnmarkDone(doneTask.permission_hints, {
        isTerminal: false,
        task: doneTask,
      }),
    ).toBe(true)
    expect(
      canShowActionPlanTaskUnmarkDone(doneTask.permission_hints, {
        isTerminal: true,
        task: doneTask,
      }),
    ).toBe(false)
  })
})
