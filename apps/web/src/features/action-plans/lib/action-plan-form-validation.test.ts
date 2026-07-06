import { describe, expect, it } from 'vitest'

import { buildActionPlanCreateRequest } from '@/features/action-plans/lib/action-plan-create-payload'
import {
  createActionPlanTaskDraft,
  validateActionPlanCreateForm,
  validateActionPlanCreatePlanningErrors,
} from '@/features/action-plans/lib/action-plan-form-validation'
import { createActionPlanEventPlanningDraft } from '@/features/action-plans/lib/action-plan-event-planning-form'
import { createActionPlanScheduleDraft } from '@/features/action-plans/lib/action-plan-schedule-form'

const emptySchedule = createActionPlanScheduleDraft()

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
        schedule: emptySchedule,
      },
      { canDefineCrossPoleTasks: false },
    )

    expect(errors.title).toBeTruthy()
    expect(errors.pilotBusinessUnitId).toBeTruthy()
    expect(errors.tasks).toBeTruthy()
  })
})

describe('validateActionPlanCreatePlanningErrors', () => {
  it('surfaces recurrence end date errors with planning field keys', () => {
    const errors = validateActionPlanCreatePlanningErrors(
      {
        ...createActionPlanEventPlanningDraft(),
        repeatEnabled: true,
        startDate: '2026-07-01',
        recurrenceDays: ['monday'],
        recurrenceEndDate: '',
        startTime: '09:00',
        endTime: '10:00',
      },
      { saveToLibrary: true },
    )

    expect(errors.recurrenceEndDate).toBeTruthy()
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
      schedule: emptySchedule,
    })

    expect(payload.is_reusable).toBe(true)
    expect(payload.assignees).toEqual([])
    expect(payload.tasks).toEqual([
      { task: 'Task 1', business_unit_id: 'bu-1', position: 1 },
    ])
    expect(payload.source_signal_id).toBeUndefined()
  })

  it('includes source_signal_id when sourceSignalId is provided', () => {
    const payload = buildActionPlanCreateRequest({
      title: 'Signal plan',
      description: '',
      pilotBusinessUnitId: 'bu-1',
      requiresValidation: true,
      saveToLibrary: false,
      useSharedChronology: false,
      sharedStartAt: '',
      sharedEndAt: '',
      sharedVisibleFrom: '',
      tasks: [{ id: '1', task: 'Task 1', businessUnitId: 'bu-1' }],
      assignees: [],
      schedule: emptySchedule,
      sourceSignalId: 'sig-1',
    })

    expect(payload.source_signal_id).toBe('sig-1')
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
    schedule: emptySchedule,
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
