import { describe, expect, it } from 'vitest'

import {
  hasAssignmentFormErrors,
  hasTemplateScheduleFormErrors,
  validateAssignmentForm,
  validateChecklistCreateForm,
  validateRegisteredTemplateCreate,
  validateTask,
  validateTemplateScheduleForm,
} from './checklist-form-validation'

describe('checklist-form-validation', () => {
  it('validates assignment form required fields', () => {
    const errors = validateAssignmentForm({
      assignedTo: '',
      startDate: '',
      endDate: '',
      startAt: '',
      endAt: '',
      recurrenceDays: [],
    })

    expect(hasAssignmentFormErrors(errors)).toBe(true)
    expect(errors.assignedTo).toBeTruthy()
    expect(errors.startDate).toBeTruthy()
    expect(errors.startAt).toBeTruthy()
    expect(errors.endAt).toBeTruthy()
  })

  it('rejects end time before start time on same day', () => {
    const errors = validateAssignmentForm({
      assignedTo: 'member-1',
      startDate: '2026-06-10',
      endDate: '2026-06-10',
      startAt: '10:00',
      endAt: '09:00',
      recurrenceDays: [],
    })

    expect(errors.endAt).toBeTruthy()
  })

  it('rejects end date before start date', () => {
    const errors = validateAssignmentForm({
      assignedTo: 'member-1',
      startDate: '2026-06-19',
      endDate: '2026-06-09',
      startAt: '10:00',
      endAt: '11:00',
      recurrenceDays: ['monday'],
    })

    expect(errors.endDate).toBeTruthy()
  })

  it('rejects duplicate recurrence days', () => {
    const errors = validateAssignmentForm({
      assignedTo: 'member-1',
      startDate: '2026-06-10',
      endDate: '2026-06-20',
      startAt: '10:00',
      endAt: '12:00',
      recurrenceDays: ['monday', 'monday'],
    })

    expect(errors.recurrenceDays).toBeTruthy()
  })

  it('requires business unit and tasks for registered template create', () => {
    expect(
      validateRegisteredTemplateCreate({
        title: 'Routine',
        businessUnitId: '',
        taskCount: 1,
        assignNow: false,
        assignedTo: '',
      }),
    ).toBeTruthy()
    expect(
      validateRegisteredTemplateCreate({
        title: 'Routine',
        businessUnitId: 'bu-1',
        taskCount: 1,
        assignNow: false,
        assignedTo: '',
      }),
    ).toBeNull()
  })

  it('requires task', () => {
    expect(validateTask('')).toBe('La tâche est obligatoire.')
    expect(validateTask('Vérifier stock')).toBeNull()
  })

  it('validates unified create form for template and assignment modes', () => {
    const base = {
      title: 'Routine',
      businessUnitId: 'bu-1',
      taskValues: ['Vérifier stock'],
      assignmentMode: 'none' as const,
    }

    expect(validateChecklistCreateForm(base)).toEqual({ ok: true })

    expect(
      validateChecklistCreateForm({
        ...base,
        businessUnitId: '',
      }),
    ).toMatchObject({
      ok: false,
      openBusinessUnitSheet: true,
    })

    expect(
      validateChecklistCreateForm({
        ...base,
        assignmentMode: 'create_now',
        assignmentValues: {
          assignedTo: '',
          startDate: '',
          endDate: '',
          startAt: '',
          endAt: '',
          recurrenceDays: [],
        },
      }),
    ).toMatchObject({
      ok: false,
      openOptions: true,
      assignmentErrors: expect.objectContaining({ assignedTo: expect.any(String) }),
    })
  })

  it('validates template schedule form end after start', () => {
    const errors = validateTemplateScheduleForm({
      assignedTo: 'member-1',
      startAt: '09:30',
      endAt: '09:00',
      recurrenceDays: [],
      recurrenceEndDate: '',
      canLaunchExecution: true,
      canCreateAssignment: true,
    })

    expect(hasTemplateScheduleFormErrors(errors)).toBe(true)
    expect(errors.endAt).toBeTruthy()
  })

  it('requires recurrence end date when recurring', () => {
    const errors = validateTemplateScheduleForm({
      assignedTo: 'member-1',
      startAt: '09:00',
      endAt: '10:00',
      recurrenceDays: ['monday'],
      recurrenceEndDate: '',
      canLaunchExecution: true,
      canCreateAssignment: true,
    })

    expect(errors.recurrenceEndDate).toBeTruthy()
  })

  it('rejects recurrence end date before reference date', () => {
    const errors = validateTemplateScheduleForm(
      {
        assignedTo: 'member-1',
        startAt: '09:00',
        endAt: '10:00',
        recurrenceDays: ['monday'],
        recurrenceEndDate: '2026-06-10',
        canLaunchExecution: true,
        canCreateAssignment: true,
      },
      { referenceDateIso: '2026-06-17' },
    )

    expect(errors.recurrenceEndDate).toBe(
      'La fin de la récurrence ne peut pas être dans le passé.',
    )
  })
})
