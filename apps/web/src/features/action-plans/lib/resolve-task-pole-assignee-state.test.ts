import { describe, expect, it } from 'vitest'

import { createActionPlanTaskDraft } from '@/features/action-plans/lib/action-plan-form-validation'
import {
  applyAssigneeSelectionToTask,
  isAdminAssigneeTask,
  resolveTaskPoleAssigneeState,
  shouldClearAssigneeOnPoleChange,
} from '@/features/action-plans/lib/resolve-task-pole-assignee-state'

const businessUnits = [
  { id: 'bu-1', label: 'Restaurant' },
  { id: 'bu-2', label: 'Bar' },
]

describe('resolveTaskPoleAssigneeState', () => {
  it('allows assignee pick without pole', () => {
    const state = resolveTaskPoleAssigneeState({
      task: createActionPlanTaskDraft(''),
      pilotBusinessUnitId: 'bu-1',
      businessUnits,
    })

    expect(state.canPickAssignee).toBe(true)
    expect(state.poleLocked).toBe(false)
  })

  it('locks pole when assignee has a single business unit', () => {
    const task = {
      ...createActionPlanTaskDraft(''),
      assigneeMembershipId: 'member-1',
      assigneeDisplayName: 'Nami',
      assigneeBusinessUnitIds: ['bu-2'],
      businessUnitId: 'bu-2',
    }
    const state = resolveTaskPoleAssigneeState({
      task,
      pilotBusinessUnitId: 'bu-1',
      businessUnits,
    })

    expect(state.poleLocked).toBe(true)
    expect(state.poleOptions).toEqual([{ id: 'bu-2', label: 'Bar' }])
  })

  it('adds fallback pole option when assignee scope is outside visible business units', () => {
    const task = {
      ...createActionPlanTaskDraft(''),
      assigneeMembershipId: 'member-1',
      assigneeDisplayName: 'Manager maintenance',
      assigneeBusinessUnitIds: ['bu-hidden'],
    }
    const state = resolveTaskPoleAssigneeState({
      task,
      pilotBusinessUnitId: 'bu-1',
      businessUnits,
    })

    expect(state.poleLocked).toBe(true)
    expect(state.effectiveBusinessUnitId).toBe('bu-hidden')
    expect(state.poleOptions).toEqual([{ id: 'bu-hidden', label: "Pôle de l'assigné" }])
  })

  it('requires pole choice when assignee has multiple business units', () => {
    const task = {
      ...createActionPlanTaskDraft(''),
      assigneeMembershipId: 'member-1',
      assigneeDisplayName: 'Nami',
      assigneeBusinessUnitIds: ['bu-1', 'bu-2'],
    }
    const state = resolveTaskPoleAssigneeState({
      task,
      pilotBusinessUnitId: 'bu-1',
      businessUnits,
    })

    expect(state.requiresPoleChoice).toBe(true)
    expect(state.poleOptions).toEqual(businessUnits)
  })

  it('keeps pole selectable when assignee is owner or director', () => {
    const task = {
      ...createActionPlanTaskDraft(''),
      assigneeMembershipId: 'member-1',
      assigneeDisplayName: 'Director',
      assigneeBusinessUnitIds: [],
    }
    const state = resolveTaskPoleAssigneeState({
      task,
      pilotBusinessUnitId: 'bu-1',
      businessUnits,
    })

    expect(state.poleLocked).toBe(false)
    expect(state.requiresPoleChoice).toBe(true)
    expect(state.effectiveBusinessUnitId).toBe('')
    expect(state.poleOptions).toEqual(businessUnits)
  })

  it('shows chosen pole for admin assignee without using pilot fallback', () => {
    const task = {
      ...createActionPlanTaskDraft('bu-2'),
      assigneeMembershipId: 'member-1',
      assigneeDisplayName: 'Owner',
      assigneeBusinessUnitIds: [],
    }
    const state = resolveTaskPoleAssigneeState({
      task,
      pilotBusinessUnitId: 'bu-1',
      businessUnits,
    })

    expect(state.poleLocked).toBe(false)
    expect(state.requiresPoleChoice).toBe(false)
    expect(state.effectiveBusinessUnitId).toBe('bu-2')
  })

  it('keeps all pole options for unassigned task even when business unit is set', () => {
    const state = resolveTaskPoleAssigneeState({
      task: createActionPlanTaskDraft('bu-2'),
      pilotBusinessUnitId: 'bu-1',
      businessUnits,
    })

    expect(state.poleOptions).toEqual(businessUnits)
    expect(state.effectiveBusinessUnitId).toBe('bu-2')
  })
})

describe('isAdminAssigneeTask', () => {
  it('returns true for owner or director assignee', () => {
    const task = {
      ...createActionPlanTaskDraft(''),
      assigneeMembershipId: 'member-1',
      assigneeBusinessUnitIds: [],
    }

    expect(isAdminAssigneeTask(task)).toBe(true)
  })

  it('returns false without assignee', () => {
    expect(isAdminAssigneeTask(createActionPlanTaskDraft(''))).toBe(false)
  })
})

describe('shouldClearAssigneeOnPoleChange', () => {
  it('does not clear owner assignee on pole change', () => {
    const task = {
      ...createActionPlanTaskDraft(''),
      assigneeMembershipId: 'member-owner',
      assigneeDisplayName: 'Owner',
      assigneeBusinessUnitIds: [],
    }

    expect(shouldClearAssigneeOnPoleChange(task, 'bu-2')).toBe(false)
  })

  it('does not clear director assignee on pole change', () => {
    const task = {
      ...createActionPlanTaskDraft(''),
      assigneeMembershipId: 'member-director',
      assigneeDisplayName: 'Director',
      assigneeBusinessUnitIds: [],
    }

    expect(shouldClearAssigneeOnPoleChange(task, 'bu-1')).toBe(false)
  })

  it('clears single-scope manager when pole changes outside scope', () => {
    const task = {
      ...createActionPlanTaskDraft('bu-1'),
      assigneeMembershipId: 'member-1',
      assigneeDisplayName: 'Manager',
      assigneeBusinessUnitIds: ['bu-1'],
    }

    expect(shouldClearAssigneeOnPoleChange(task, 'bu-2')).toBe(true)
    expect(shouldClearAssigneeOnPoleChange(task, 'bu-1')).toBe(false)
  })

  it('clears multi-scope assignee when pole is outside scopes', () => {
    const task = {
      ...createActionPlanTaskDraft('bu-1'),
      assigneeMembershipId: 'member-1',
      assigneeDisplayName: 'Multi',
      assigneeBusinessUnitIds: ['bu-1', 'bu-2'],
    }

    expect(shouldClearAssigneeOnPoleChange(task, 'bu-2')).toBe(false)
    expect(shouldClearAssigneeOnPoleChange(task, 'bu-3')).toBe(true)
  })
})

describe('applyAssigneeSelectionToTask', () => {
  it('auto-fills business unit for single-scope assignee', () => {
    const nextTask = applyAssigneeSelectionToTask(createActionPlanTaskDraft(''), {
      membershipId: 'member-1',
      displayName: 'Nami',
      businessUnitIds: ['bu-2'],
    })

    expect(nextTask.businessUnitId).toBe('bu-2')
    expect(nextTask.assigneeMembershipId).toBe('member-1')
  })

  it('clears business unit when selecting owner or director assignee', () => {
    const nextTask = applyAssigneeSelectionToTask(
      {
        ...createActionPlanTaskDraft('bu-2'),
        assigneeMembershipId: 'member-1',
        assigneeDisplayName: 'Nami',
        assigneeBusinessUnitIds: ['bu-2'],
      },
      {
        membershipId: 'member-2',
        displayName: 'Director',
        businessUnitIds: [],
      },
    )

    expect(nextTask.businessUnitId).toBe('')
    expect(nextTask.assigneeBusinessUnitIds).toEqual([])
  })
})
