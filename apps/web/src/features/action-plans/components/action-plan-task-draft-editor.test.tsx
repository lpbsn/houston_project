// @vitest-environment jsdom

import { createElement } from 'react'
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  ActionPlanTaskDraftEditor,
  createActionPlanTaskDraftEditorItem,
} from '@/features/action-plans/components/action-plan-task-draft-editor'
import {
  createActionPlanTaskDraft,
  type ActionPlanTaskDraft,
} from '@/features/action-plans/lib/action-plan-form-validation'

let lastAssigneeSheetProps: Record<string, unknown> | null = null

vi.mock('@/features/action-plans/components/action-plan-task-assignee-sheet', () => ({
  ActionPlanTaskAssigneeSheet: (props: Record<string, unknown>) => {
    lastAssigneeSheetProps = props
    return null
  },
}))

afterEach(() => {
  cleanup()
  lastAssigneeSheetProps = null
})

describe('ActionPlanTaskDraftEditor', () => {
  it('creates new tasks with an empty business unit', () => {
    const task = createActionPlanTaskDraftEditorItem()

    expect(task.businessUnitId).toBe('')
    expect(task.assigneeBusinessUnitIds).toEqual([])
  })

  it('shows pole picker for non cross-pole users', () => {
    render(
      createElement(ActionPlanTaskDraftEditor, {
        tasks: [createActionPlanTaskDraft('')],
        establishmentId: 'est-1',
        pilotBusinessUnitId: 'bu-1',
        canDefineCrossPoleTasks: false,
        businessUnits: [{ id: 'bu-1', label: 'Restaurant' }],
        onTasksChange: vi.fn(),
      }),
    )

    fireEvent.click(screen.getByRole('button', { name: 'Options avancées' }))

    expect(screen.getByRole('button', { name: "Pôle d'activité" })).toBeTruthy()
  })

  it('allows assignee picker before a task pole is selected', () => {
    render(
      createElement(ActionPlanTaskDraftEditor, {
        tasks: [{ ...createActionPlanTaskDraft(''), task: 'Contrôler la température' }],
        establishmentId: 'est-1',
        pilotBusinessUnitId: 'bu-1',
        canDefineCrossPoleTasks: false,
        businessUnits: [{ id: 'bu-1', label: 'Restaurant' }],
        onTasksChange: vi.fn(),
      }),
    )

    fireEvent.click(screen.getByRole('button', { name: 'Options avancées' }))
    fireEvent.click(screen.getByRole('button', { name: 'Choisir' }))

    expect(screen.getByRole('button', { name: 'Choisir' })).toHaveProperty('disabled', false)
    expect(screen.queryByText('Sélectionnez d’abord un pôle d’activité.')).toBeNull()
    expect(lastAssigneeSheetProps?.businessUnitId).toBe('bu-1')
  })

  it('shows pilot fallback hint when pole and assignee are empty', () => {
    render(
      createElement(ActionPlanTaskDraftEditor, {
        tasks: [{ ...createActionPlanTaskDraft(''), task: 'Contrôler la température' }],
        establishmentId: 'est-1',
        pilotBusinessUnitId: 'bu-1',
        canDefineCrossPoleTasks: false,
        businessUnits: [{ id: 'bu-1', label: 'Restaurant' }],
        onTasksChange: vi.fn(),
      }),
    )

    fireEvent.click(screen.getByRole('button', { name: 'Options avancées' }))

    expect(
      screen.getByText('Sans pôle explicite, le pôle pilote sera utilisé.'),
    ).toBeTruthy()
  })

  it('shows locked pole when assignee has a single scope', () => {
    render(
      createElement(ActionPlanTaskDraftEditor, {
        tasks: [
          {
            ...createActionPlanTaskDraft(''),
            task: 'Contrôler la température',
            assigneeMembershipId: 'member-1',
            assigneeDisplayName: 'Manager restaurant',
            assigneeBusinessUnitIds: ['bu-1'],
            businessUnitId: 'bu-1',
          },
        ],
        establishmentId: 'est-1',
        pilotBusinessUnitId: 'bu-1',
        canDefineCrossPoleTasks: false,
        businessUnits: [{ id: 'bu-1', label: 'Restaurant' }],
        onTasksChange: vi.fn(),
      }),
    )

    fireEvent.click(screen.getByRole('button', { name: 'Options avancées' }))

    expect(screen.getByText('Restaurant')).toBeTruthy()
    expect(screen.queryByRole('button', { name: "Pôle d'activité" })).toBeNull()
  })

  it('shows selectable pole for admin assignee with explicit pole choice', () => {
    render(
      createElement(ActionPlanTaskDraftEditor, {
        tasks: [
          {
            ...createActionPlanTaskDraft('bu-1'),
            task: 'Contrôler la température',
            assigneeMembershipId: 'member-1',
            assigneeDisplayName: 'Director',
            assigneeBusinessUnitIds: [],
          },
        ],
        establishmentId: 'est-1',
        pilotBusinessUnitId: 'bu-1',
        canDefineCrossPoleTasks: false,
        businessUnits: [{ id: 'bu-1', label: 'Restaurant' }],
        onTasksChange: vi.fn(),
      }),
    )

    fireEvent.click(screen.getByRole('button', { name: 'Options avancées' }))

    expect(screen.getByRole('button', { name: "Pôle d'activité" })).toBeTruthy()
    expect(screen.getByText('Restaurant')).toBeTruthy()
  })

  it('prompts pole choice for admin assignee without pole', () => {
    render(
      createElement(ActionPlanTaskDraftEditor, {
        tasks: [
          {
            ...createActionPlanTaskDraft(''),
            task: 'Contrôler la température',
            assigneeMembershipId: 'member-1',
            assigneeDisplayName: 'Director',
            assigneeBusinessUnitIds: [],
          },
        ],
        establishmentId: 'est-1',
        pilotBusinessUnitId: 'bu-1',
        canDefineCrossPoleTasks: false,
        businessUnits: [{ id: 'bu-1', label: 'Restaurant' }],
        onTasksChange: vi.fn(),
      }),
    )

    fireEvent.click(screen.getByRole('button', { name: 'Options avancées' }))

    expect(
      screen.getByText("Choisissez un pôle d'activité pour cette tâche."),
    ).toBeTruthy()
    expect(screen.queryByText('Sans pôle explicite, le pôle pilote sera utilisé.')).toBeNull()
    expect(screen.getByRole('button', { name: "Pôle d'activité" })).toHaveProperty(
      'textContent',
      '—',
    )
  })

  it('clears pole when assignee is cleared', () => {
    const onTasksChange = vi.fn()
    const initialTasks = [
      {
        ...createActionPlanTaskDraft('bu-1'),
        task: 'Contrôler la température',
        assigneeMembershipId: 'member-1',
        assigneeDisplayName: 'Manager restaurant',
        assigneeBusinessUnitIds: ['bu-1'],
      },
    ]

    render(
      createElement(ActionPlanTaskDraftEditor, {
        tasks: initialTasks,
        establishmentId: 'est-1',
        pilotBusinessUnitId: 'bu-1',
        canDefineCrossPoleTasks: false,
        businessUnits: [{ id: 'bu-1', label: 'Restaurant' }],
        onTasksChange,
      }),
    )

    fireEvent.click(screen.getByRole('button', { name: 'Options avancées' }))
    fireEvent.click(screen.getByRole('button', { name: 'Effacer' }))

    const update = onTasksChange.mock.calls[0][0] as
      | ActionPlanTaskDraft[]
      | ((previous: ActionPlanTaskDraft[]) => ActionPlanTaskDraft[])
    const nextTasks = typeof update === 'function' ? update(initialTasks) : update

    expect(nextTasks).toEqual([
      expect.objectContaining({
        assigneeMembershipId: '',
        assigneeDisplayName: '',
        assigneeBusinessUnitIds: [],
        businessUnitId: '',
      }),
    ])
  })

  it('does not show pole in the title meta line', () => {
    render(
      createElement(ActionPlanTaskDraftEditor, {
        tasks: [
          {
            ...createActionPlanTaskDraft('bu-1'),
            task: 'Contrôler la température',
            assigneeDisplayName: 'Nami',
          },
        ],
        establishmentId: 'est-1',
        pilotBusinessUnitId: 'bu-1',
        canDefineCrossPoleTasks: false,
        businessUnits: [{ id: 'bu-1', label: 'Restaurant' }],
        onTasksChange: vi.fn(),
      }),
    )

    expect(screen.getByText('Nami')).toBeTruthy()
    expect(screen.queryByText('Restaurant')).toBeNull()
  })

  it('keeps director assignee when opening pole picker', () => {
    const onTasksChange = vi.fn()
    const businessUnits = [
      { id: 'bu-comm', label: 'Communication' },
      { id: 'bu-rest', label: 'Restaurant' },
      { id: 'bu-bar', label: 'Bar' },
    ]

    render(
      createElement(ActionPlanTaskDraftEditor, {
        tasks: [
          {
            ...createActionPlanTaskDraft(''),
            task: 'Contrôler la température',
            assigneeMembershipId: 'member-director',
            assigneeDisplayName: 'Director',
            assigneeBusinessUnitIds: [],
          },
        ],
        establishmentId: 'est-1',
        pilotBusinessUnitId: 'bu-rest',
        canDefineCrossPoleTasks: true,
        businessUnits,
        onTasksChange,
      }),
    )

    fireEvent.click(screen.getByRole('button', { name: 'Options avancées' }))
    fireEvent.click(screen.getByRole('button', { name: "Pôle d'activité" }))

    expect(onTasksChange).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: 'Communication' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Restaurant' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Bar' })).toBeTruthy()
  })

  it('keeps owner assignee when opening pole picker', () => {
    const onTasksChange = vi.fn()
    const businessUnits = [
      { id: 'bu-comm', label: 'Communication' },
      { id: 'bu-rest', label: 'Restaurant' },
      { id: 'bu-bar', label: 'Bar' },
    ]

    render(
      createElement(ActionPlanTaskDraftEditor, {
        tasks: [
          {
            ...createActionPlanTaskDraft(''),
            task: 'Contrôler la température',
            assigneeMembershipId: 'member-owner',
            assigneeDisplayName: 'Owner',
            assigneeBusinessUnitIds: [],
          },
        ],
        establishmentId: 'est-1',
        pilotBusinessUnitId: 'bu-rest',
        canDefineCrossPoleTasks: true,
        businessUnits,
        onTasksChange,
      }),
    )

    fireEvent.click(screen.getByRole('button', { name: 'Options avancées' }))
    fireEvent.click(screen.getByRole('button', { name: "Pôle d'activité" }))

    expect(onTasksChange).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: 'Communication' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Restaurant' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Bar' })).toBeTruthy()
  })

  it('shows all pole options for unassigned task when opening picker with non-default pilot', () => {
    const onTasksChange = vi.fn()
    const businessUnits = [
      { id: 'bu-comm', label: 'Communication' },
      { id: 'bu-coworking', label: 'Coworking' },
      { id: 'bu-bar', label: 'Bar' },
    ]

    render(
      createElement(ActionPlanTaskDraftEditor, {
        tasks: [{ ...createActionPlanTaskDraft(''), task: 'Contrôler la température' }],
        establishmentId: 'est-1',
        pilotBusinessUnitId: 'bu-coworking',
        canDefineCrossPoleTasks: true,
        businessUnits,
        onTasksChange,
      }),
    )

    fireEvent.click(screen.getByRole('button', { name: 'Options avancées' }))
    expect(screen.getByRole('button', { name: "Pôle d'activité" })).toHaveProperty(
      'textContent',
      'Coworking',
    )
    fireEvent.click(screen.getByRole('button', { name: "Pôle d'activité" }))

    expect(onTasksChange).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: 'Communication' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Coworking' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Bar' })).toBeTruthy()
  })

  it('shows inline task errors and opens advanced options once on guidance nonce', () => {
    const draft = {
      ...createActionPlanTaskDraft(''),
      task: 'Task 1',
      assigneeMembershipId: 'member-1',
      assigneeDisplayName: 'Nami',
      assigneeBusinessUnitIds: ['bu-1', 'bu-2'],
    }
    const poleKey = `tasks.${draft.id}.businessUnitId`

    const { rerender } = render(
      createElement(ActionPlanTaskDraftEditor, {
        tasks: [draft],
        establishmentId: 'est-1',
        pilotBusinessUnitId: 'bu-1',
        canDefineCrossPoleTasks: false,
        businessUnits: [
          { id: 'bu-1', label: 'Restaurant' },
          { id: 'bu-2', label: 'Bar' },
        ],
        fieldErrors: { [poleKey]: 'Choisissez le pôle de l’assigné pour chaque tâche concernée.' },
        expandAdvancedNonce: 1,
        expandAdvancedTaskIds: [draft.id],
        onTasksChange: vi.fn(),
      }),
    )

    expect(
      screen.getByText('Choisissez le pôle de l’assigné pour chaque tâche concernée.'),
    ).toBeTruthy()
    expect(screen.getByRole('button', { name: "Pôle d'activité" })).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: 'Options avancées' }))
    expect(screen.queryByRole('button', { name: "Pôle d'activité" })).toBeNull()

    rerender(
      createElement(ActionPlanTaskDraftEditor, {
        tasks: [draft],
        establishmentId: 'est-1',
        pilotBusinessUnitId: 'bu-1',
        canDefineCrossPoleTasks: false,
        businessUnits: [
          { id: 'bu-1', label: 'Restaurant' },
          { id: 'bu-2', label: 'Bar' },
        ],
        fieldErrors: { [poleKey]: 'Choisissez le pôle de l’assigné pour chaque tâche concernée.' },
        expandAdvancedNonce: 1,
        expandAdvancedTaskIds: [draft.id],
        onTasksChange: vi.fn(),
      }),
    )

    expect(screen.queryByRole('button', { name: "Pôle d'activité" })).toBeNull()
  })

  it('keeps both task title patches from the same render before any intermediate rerender', () => {
    const first = { ...createActionPlanTaskDraft('bu-1'), id: 'task-1', task: 'Titre A' }
    const second = { ...createActionPlanTaskDraft('bu-1'), id: 'task-2', task: 'Titre B' }
    const initial = [first, second]
    let tasks = initial

    // Freeze the tasks prop so both handlers close over the same render snapshot.
    // Parent applies each update onto the latest committed list (functional-setState shape).
    render(
      createElement(ActionPlanTaskDraftEditor, {
        tasks: initial,
        establishmentId: 'est-1',
        pilotBusinessUnitId: 'bu-1',
        canDefineCrossPoleTasks: false,
        businessUnits: [{ id: 'bu-1', label: 'Restaurant' }],
        onTasksChange: (update) => {
          tasks =
            typeof update === 'function'
              ? update(tasks)
              : update
        },
      }),
    )

    const titleInputs = screen.getAllByLabelText('Titre de la tâche')
    expect(titleInputs).toHaveLength(2)

    act(() => {
      fireEvent.change(titleInputs[0], { target: { value: 'Titre batch 1' } })
      fireEvent.change(titleInputs[1], { target: { value: 'Titre batch 2' } })
    })

    expect(tasks.map((task) => ({ id: task.id, task: task.task }))).toEqual([
      { id: 'task-1', task: 'Titre batch 1' },
      { id: 'task-2', task: 'Titre batch 2' },
    ])
  })
})
