import { describe, expect, it } from 'vitest'

import { getActionPlanTaskActionOptions } from '@/features/action-plans/components/action-plan-execution-task-actions-sheet'
import type { ActionPlanTaskExecution } from '@/features/action-plans/types'

function buildTask(overrides: Partial<ActionPlanTaskExecution> = {}): ActionPlanTaskExecution {
  return {
    id: 'task-1',
    task: 'Nettoyer',
    position: 1,
    status: 'pending',
    business_unit: { id: 'bu-1', specific_name: 'Restaurant', instance_description: '', active: true, generic: { key: 'restaurant', label: 'Restaurant', description: '', unit_type: 'dedicated' } },
    observation_id: null,
    skipped_reason: null,
    completed_at: null,
    skipped_at: null,
    observation_created_at: null,
    permission_hints: {
      can_mark_done: true,
      can_unmark_done: false,
      can_skip: true,
      can_create_observation: true,
    },
    ...overrides,
  } as ActionPlanTaskExecution
}

describe('getActionPlanTaskActionOptions', () => {
  it('returns observation and skip when both hints are true', () => {
    const options = getActionPlanTaskActionOptions(buildTask(), { isTerminal: false })

    expect(options.map((option) => option.id)).toEqual(['observation', 'skip'])
  })

  it('returns only skip when observation hint is false', () => {
    const options = getActionPlanTaskActionOptions(
      buildTask({
        permission_hints: {
          can_mark_done: true,
          can_unmark_done: false,
          can_skip: true,
          can_create_observation: false,
        },
      }),
      { isTerminal: false },
    )

    expect(options.map((option) => option.id)).toEqual(['skip'])
  })

  it('returns empty list for terminal execution', () => {
    const options = getActionPlanTaskActionOptions(buildTask(), { isTerminal: true })

    expect(options).toEqual([])
  })

  it('returns empty list for non-pending task', () => {
    const options = getActionPlanTaskActionOptions(
      buildTask({ status: 'done' }),
      { isTerminal: false },
    )

    expect(options).toEqual([])
  })
})
