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
  it('requires title and pilot business unit', () => {
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
        tasks: [],
        assignees: [],
        schedule: emptySchedule,
      },
      { canDefineCrossPoleTasks: false },
    )

    expect(errors.title).toBeTruthy()
    expect(errors.pilotBusinessUnitId).toBeTruthy()
    expect(errors.tasks).toBeUndefined()
  })

  it('allows non-empty tasks without explicit business unit when pilot is set', () => {
    const errors = validateActionPlanCreateForm(
      {
        title: 'Plan',
        description: '',
        pilotBusinessUnitId: 'bu-1',
        requiresValidation: false,
        saveToLibrary: true,
        useSharedChronology: false,
        sharedStartAt: '',
        sharedEndAt: '',
        sharedVisibleFrom: '',
        tasks: [{ ...createActionPlanTaskDraft(''), task: 'Task 1' }],
        assignees: [],
        schedule: emptySchedule,
      },
      { canDefineCrossPoleTasks: false },
    )

    expect(errors.tasks).toBeUndefined()
  })

  it('requires pole choice when assignee has multiple business units', () => {
    const errors = validateActionPlanCreateForm(
      {
        title: 'Plan',
        description: '',
        pilotBusinessUnitId: 'bu-1',
        requiresValidation: false,
        saveToLibrary: true,
        useSharedChronology: false,
        sharedStartAt: '',
        sharedEndAt: '',
        sharedVisibleFrom: '',
        tasks: [
          {
            ...createActionPlanTaskDraft(''),
            task: 'Task 1',
            assigneeMembershipId: 'member-1',
            assigneeDisplayName: 'Nami',
            assigneeBusinessUnitIds: ['bu-1', 'bu-2'],
          },
        ],
        assignees: [],
        schedule: emptySchedule,
      },
      { canDefineCrossPoleTasks: false },
    )

    expect(errors.tasks).toBe('Choisissez le pôle de l’assigné pour chaque tâche concernée.')
  })

  it('requires pole choice when assignee is owner or director', () => {
    const errors = validateActionPlanCreateForm(
      {
        title: 'Plan',
        description: '',
        pilotBusinessUnitId: 'bu-1',
        requiresValidation: false,
        saveToLibrary: true,
        useSharedChronology: false,
        sharedStartAt: '',
        sharedEndAt: '',
        sharedVisibleFrom: '',
        tasks: [
          {
            ...createActionPlanTaskDraft(''),
            task: 'Task 1',
            assigneeMembershipId: 'member-1',
            assigneeDisplayName: 'Director',
            assigneeBusinessUnitIds: [],
          },
        ],
        assignees: [],
        schedule: emptySchedule,
      },
      { canDefineCrossPoleTasks: false },
    )

    expect(errors.tasks).toBe(
      'Sélectionnez un pôle d’activité pour chaque tâche assignée à un Owner ou un Director.',
    )
  })

  it('allows admin assignee when explicit pole is selected', () => {
    const errors = validateActionPlanCreateForm(
      {
        title: 'Plan',
        description: '',
        pilotBusinessUnitId: 'bu-1',
        requiresValidation: false,
        saveToLibrary: true,
        useSharedChronology: false,
        sharedStartAt: '',
        sharedEndAt: '',
        sharedVisibleFrom: '',
        tasks: [
          {
            ...createActionPlanTaskDraft('bu-1'),
            task: 'Task 1',
            assigneeMembershipId: 'member-1',
            assigneeDisplayName: 'Owner',
            assigneeBusinessUnitIds: [],
          },
        ],
        assignees: [],
        schedule: emptySchedule,
      },
      { canDefineCrossPoleTasks: true },
    )

    expect(errors.tasks).toBeUndefined()
  })

  it('requires business unit on non-empty tasks when pilot is missing', () => {
    const errors = validateActionPlanCreateForm(
      {
        title: 'Plan',
        description: '',
        pilotBusinessUnitId: '',
        requiresValidation: false,
        saveToLibrary: true,
        useSharedChronology: false,
        sharedStartAt: '',
        sharedEndAt: '',
        sharedVisibleFrom: '',
        tasks: [{ ...createActionPlanTaskDraft(''), task: 'Task 1' }],
        assignees: [],
        schedule: emptySchedule,
      },
      { canDefineCrossPoleTasks: false },
    )

    expect(errors.tasks).toBe('Chaque tâche doit avoir un pôle d’activité ou un pôle pilote.')
  })

  it('accepts form without tasks when title and pilot business unit are set', () => {
    const errors = validateActionPlanCreateForm(
      {
        title: 'Plan sans tâche',
        description: '',
        pilotBusinessUnitId: 'bu-1',
        requiresValidation: false,
        saveToLibrary: true,
        useSharedChronology: false,
        sharedStartAt: '',
        sharedEndAt: '',
        sharedVisibleFrom: '',
        tasks: [],
        assignees: [],
        schedule: emptySchedule,
      },
      { canDefineCrossPoleTasks: false },
    )

    expect(errors).toEqual({})
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
      tasks: [{ ...createActionPlanTaskDraft('bu-1'), task: 'Task 1' }],
      assignees: [],
      schedule: emptySchedule,
    })

    expect(payload.is_reusable).toBe(true)
    expect(payload.assignees).toEqual([])
    expect(payload.tasks).toEqual([
      {
        task: 'Task 1',
        business_unit_id: 'bu-1',
        position: 1,
        description: '',
        deadline_at: null,
        assigned_membership_id: null,
      },
    ])
    expect(payload.source_signal_id).toBeUndefined()
  })

  it('builds catalog create payload without tasks', () => {
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
      tasks: [],
      assignees: [],
      schedule: emptySchedule,
    })

    expect(payload.tasks).toEqual([])
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
      tasks: [{ ...createActionPlanTaskDraft('bu-1'), task: 'Task 1' }],
      assignees: [],
      schedule: emptySchedule,
      sourceSignalId: 'sig-1',
    })

    expect(payload.source_signal_id).toBe('sig-1')
  })

  it('defaults task business unit to pilot when omitted in draft', () => {
    const payload = buildActionPlanCreateRequest({
      title: 'Plan A',
      description: 'Desc',
      pilotBusinessUnitId: 'bu-pilot',
      requiresValidation: false,
      saveToLibrary: true,
      useSharedChronology: false,
      sharedStartAt: '',
      sharedEndAt: '',
      sharedVisibleFrom: '',
      tasks: [{ ...createActionPlanTaskDraft(''), task: 'Task without pole' }],
      assignees: [],
      schedule: emptySchedule,
    })

    expect(payload.tasks?.[0]?.business_unit_id).toBe('bu-pilot')
  })

  it('includes enriched task fields in payload', () => {
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
      tasks: [
        {
          ...createActionPlanTaskDraft('bu-1'),
          task: 'Task 1',
          description: 'Details',
          deadlineAt: '2026-07-07T14:30:00.000Z',
          assigneeMembershipId: 'member-1',
        },
      ],
      assignees: [],
      schedule: emptySchedule,
    })

    expect(payload.tasks?.[0]).toMatchObject({
      task: 'Task 1',
      business_unit_id: 'bu-1',
      description: 'Details',
      assigned_membership_id: 'member-1',
    })
    expect(payload.tasks?.[0]?.deadline_at).toBeTruthy()
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
    tasks: [{ ...createActionPlanTaskDraft('bu-1'), task: 'Task 1' }],
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
        tasks: [{ ...createActionPlanTaskDraft('bu-2'), task: 'Task 1' }],
      },
      { canDefineCrossPoleTasks: false, staffExecutionMode: staffMode },
    )
    expect(errors.tasks).toBeTruthy()
  })
})
