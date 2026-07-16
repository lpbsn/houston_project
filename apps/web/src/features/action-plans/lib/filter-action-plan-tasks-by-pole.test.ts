import { describe, expect, it } from 'vitest'

import type { ActionPlanTaskExecution } from '@/features/action-plans/types'

import { filterActionPlanTasksByPole } from './filter-action-plan-tasks-by-pole'

function buildTask(
  overrides: Partial<ActionPlanTaskExecution> & Pick<ActionPlanTaskExecution, 'id' | 'business_unit'>,
): ActionPlanTaskExecution {
  return {
    task: 'Task',
    description: '',
    deadline_at: null,
    assigned_membership_id: null,
    assigned_display_name: null,
    position: 1,
    status: 'pending',
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

describe('filterActionPlanTasksByPole', () => {
  const tasks = [
    buildTask({
      id: 'task-1',
      business_unit: { id: 'bu-1', specific_name: 'Restaurant', instance_description: '', active: true, generic: { key: 'restaurant', label: 'Restaurant', description: '', unit_type: 'dedicated' } },
    }),
    buildTask({
      id: 'task-2',
      business_unit: { id: 'bu-2', specific_name: 'Maintenance', instance_description: '', active: true, generic: { key: 'maintenance', label: 'Maintenance', description: '', unit_type: 'dedicated' } },
    }),
  ]

  it('returns all tasks when businessUnitId is null', () => {
    expect(filterActionPlanTasksByPole(tasks, null)).toEqual(tasks)
  })

  it('returns matching tasks for a valid business unit id', () => {
    expect(filterActionPlanTasksByPole(tasks, 'bu-2')).toEqual([tasks[1]])
  })

  it('returns an empty array when no task matches', () => {
    expect(filterActionPlanTasksByPole(tasks, 'bu-unknown')).toEqual([])
  })
})
