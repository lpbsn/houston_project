// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ActionPlanExecutionTaskList } from '@/features/action-plans/components/action-plan-execution-task-list'
import type { ActionPlanTaskExecution } from '@/features/action-plans/types'

function buildTask(
  overrides: Partial<ActionPlanTaskExecution> & Pick<ActionPlanTaskExecution, 'id' | 'position' | 'task'>,
): ActionPlanTaskExecution {
  return {
    description: '',
    deadline_at: null,
    assigned_membership_id: null,
    assigned_display_name: null,
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

afterEach(() => {
  cleanup()
})

describe('ActionPlanExecutionTaskList', () => {
  it('renders tasks sorted by position', () => {
    render(
      createElement(ActionPlanExecutionTaskList, {
        tasks: [
          buildTask({ id: 'task-2', position: 2, task: 'Deuxième tâche' }),
          buildTask({ id: 'task-1', position: 1, task: 'Première tâche' }),
        ],
        isTerminal: false,
        isMutationPending: false,
        onMarkDone: vi.fn(),
        onUnmarkDone: vi.fn(),
        onOpenTaskActions: vi.fn(),
      }),
    )

    const titles = screen.getAllByText(/tâche$/i).map((node) => node.textContent)
    expect(titles).toEqual(['Première tâche', 'Deuxième tâche'])
  })

  it('renders each task in its own card', () => {
    const { container } = render(
      createElement(ActionPlanExecutionTaskList, {
        tasks: [
          buildTask({ id: 'task-1', position: 1, task: 'Première tâche' }),
          buildTask({ id: 'task-2', position: 2, task: 'Deuxième tâche' }),
        ],
        isTerminal: false,
        isMutationPending: false,
        onMarkDone: vi.fn(),
        onUnmarkDone: vi.fn(),
        onOpenTaskActions: vi.fn(),
      }),
    )

    expect(container.querySelectorAll('.rounded-\\[14px\\]')).toHaveLength(2)
    expect(container.querySelector('.divide-y')).toBeNull()
  })
})
