import { describe, expect, it } from 'vitest'

import { buildActionPlanCreateRequest } from '@/features/action-plans/lib/action-plan-create-payload'
import {
  createActionPlanTaskDraft,
  validateActionPlanCreateForm,
} from '@/features/action-plans/lib/action-plan-form-validation'

describe('validateActionPlanCreateForm', () => {
  it('requires title, pilot business unit, and tasks', () => {
    const errors = validateActionPlanCreateForm(
      {
        title: '',
        description: '',
        pilotBusinessUnitId: '',
        requiresValidation: true,
        saveToLibrary: true,
        useSharedChronology: true,
        sharedStartAt: '',
        sharedEndAt: '',
        sharedVisibleFrom: '',
        tasks: [createActionPlanTaskDraft()],
        assignees: [],
      },
      { canDefineCrossPoleTasks: false },
    )

    expect(errors.title).toBeTruthy()
    expect(errors.pilotBusinessUnitId).toBeTruthy()
    expect(errors.tasks).toBeTruthy()
  })
})

describe('buildActionPlanCreateRequest', () => {
  it('builds catalog create payload without assignees', () => {
    const payload = buildActionPlanCreateRequest({
      title: 'Plan A',
      description: 'Desc',
      pilotBusinessUnitId: 'bu-1',
      requiresValidation: false,
      saveToLibrary: true,
      useSharedChronology: false,
      sharedStartAt: '',
      sharedEndAt: '',
      sharedVisibleFrom: '',
      tasks: [{ id: '1', task: 'Task 1', businessUnitId: 'bu-1' }],
      assignees: [],
    })

    expect(payload.is_reusable).toBe(true)
    expect(payload.assignees).toEqual([])
    expect(payload.tasks).toEqual([
      { task: 'Task 1', business_unit_id: 'bu-1', position: 1 },
    ])
  })
})

describe('validateActionPlanCreateForm staff execution filet', () => {
  const staffValues = {
    title: 'Plan staff',
    description: '',
    pilotBusinessUnitId: 'bu-1',
    requiresValidation: false,
    saveToLibrary: false,
    useSharedChronology: true,
    sharedStartAt: '',
    sharedEndAt: '',
    sharedVisibleFrom: '',
    tasks: [{ id: '1', task: 'Task 1', businessUnitId: 'bu-1' }],
    assignees: [
      {
        id: 'a1',
        membershipId: 'member-1',
        businessUnitId: 'bu-1',
        displayName: 'Moi',
        startAt: '',
        endAt: '',
        visibleFrom: '',
      },
    ],
  }

  const staffMode = { membershipId: 'member-1', pilotBusinessUnitId: 'bu-1' }

  it('rejects staff plan with requires_validation true', () => {
    const errors = validateActionPlanCreateForm(
      { ...staffValues, requiresValidation: true },
      { canDefineCrossPoleTasks: false, staffExecutionMode: staffMode },
    )
    expect(errors.submit).toBeTruthy()
  })

  it('rejects staff plan with multiple assignees', () => {
    const errors = validateActionPlanCreateForm(
      {
        ...staffValues,
        assignees: [
          ...staffValues.assignees,
          {
            id: 'a2',
            membershipId: 'member-2',
            businessUnitId: 'bu-1',
            displayName: 'Autre',
            startAt: '',
            endAt: '',
            visibleFrom: '',
          },
        ],
      },
      { canDefineCrossPoleTasks: false, staffExecutionMode: staffMode },
    )
    expect(errors.assignees).toBeTruthy()
  })

  it('rejects staff plan with cross-pole task', () => {
    const errors = validateActionPlanCreateForm(
      {
        ...staffValues,
        tasks: [{ id: '1', task: 'Task 1', businessUnitId: 'bu-2' }],
      },
      { canDefineCrossPoleTasks: false, staffExecutionMode: staffMode },
    )
    expect(errors.tasks).toBeTruthy()
  })
})
