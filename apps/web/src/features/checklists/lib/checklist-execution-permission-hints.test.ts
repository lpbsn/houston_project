import { describe, expect, it } from 'vitest'

import type { ChecklistTaskExecution } from '../types'

import {
  canShowChecklistExecutionCancel,
  canShowChecklistExecutionTaskActions,
  hasCompleteChecklistExecutionPermissionHints,
} from './checklist-execution-permission-hints'

const pendingTask: ChecklistTaskExecution = {
  id: 'task-1',
  task: 'Check fridge',
  position: 1,
  status: 'pending',
  observation_id: null,
  skipped_reason: null,
  completed_at: null,
  skipped_at: null,
  observation_created_at: null,
}

describe('checklist-execution-permission-hints', () => {
  it('treats missing or partial hints as incomplete', () => {
    expect(hasCompleteChecklistExecutionPermissionHints(undefined)).toBe(false)
    expect(hasCompleteChecklistExecutionPermissionHints(null)).toBe(false)
    expect(hasCompleteChecklistExecutionPermissionHints({} as never)).toBe(false)
    expect(
      hasCompleteChecklistExecutionPermissionHints({
        can_execute_tasks: true,
      } as never),
    ).toBe(false)
  })

  it('shows task actions only when can_execute_tasks is true on pending tasks', () => {
    const hints = { can_execute_tasks: true, can_cancel: false }

    expect(
      canShowChecklistExecutionTaskActions(hints, {
        isTerminal: false,
        task: pendingTask,
      }),
    ).toBe(true)

    expect(
      canShowChecklistExecutionTaskActions(hints, {
        isTerminal: true,
        task: pendingTask,
      }),
    ).toBe(false)

    expect(
      canShowChecklistExecutionTaskActions(
        { can_execute_tasks: false, can_cancel: true },
        { isTerminal: false, task: pendingTask },
      ),
    ).toBe(false)
  })

  it('hides task actions when hints are absent', () => {
    expect(
      canShowChecklistExecutionTaskActions(undefined, {
        isTerminal: false,
        task: pendingTask,
      }),
    ).toBe(false)
  })

  it('shows cancel only when can_cancel is true and execution is active', () => {
    expect(
      canShowChecklistExecutionCancel(
        { can_execute_tasks: false, can_cancel: true },
        { isTerminal: false },
      ),
    ).toBe(true)

    expect(
      canShowChecklistExecutionCancel(
        { can_execute_tasks: false, can_cancel: true },
        { isTerminal: true },
      ),
    ).toBe(false)

    expect(
      canShowChecklistExecutionCancel(
        { can_execute_tasks: true, can_cancel: false },
        { isTerminal: false },
      ),
    ).toBe(false)
  })

  it('hides cancel when hints are absent', () => {
    expect(canShowChecklistExecutionCancel(undefined, { isTerminal: false })).toBe(false)
  })
})
