import { describe, expect, it } from 'vitest'

import {
  hasAssignmentFormErrors,
  validateAssignmentForm,
  validateChecklistCreateForm,
  validateFlashTodoCreate,
  validateRegisteredTemplateCreate,
  validateTask,
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

  it('requires title, business unit, assignee, and tasks for flash to-do', () => {
    expect(
      validateFlashTodoCreate({
        title: '',
        businessUnitId: 'bu-1',
        assignedTo: 'member-1',
        taskCount: 1,
      }),
    ).toBeTruthy()
    expect(
      validateFlashTodoCreate({
        title: 'Terrasse',
        businessUnitId: '',
        assignedTo: 'member-1',
        taskCount: 1,
      }),
    ).toBeTruthy()
    expect(
      validateFlashTodoCreate({
        title: 'Terrasse',
        businessUnitId: 'bu-1',
        assignedTo: '',
        taskCount: 1,
      }),
    ).toBeTruthy()
    expect(
      validateFlashTodoCreate({
        title: 'Terrasse',
        businessUnitId: 'bu-1',
        assignedTo: 'member-1',
        taskCount: 0,
      }),
    ).toBeTruthy()
    expect(
      validateFlashTodoCreate({
        title: 'Terrasse',
        businessUnitId: 'bu-1',
        assignedTo: 'member-1',
        taskCount: 2,
      }),
    ).toBeNull()
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

  it('validates unified create form for template, assignment, and flash modes', () => {
    const base = {
      title: 'Routine',
      businessUnitId: 'bu-1',
      taskValues: ['Vérifier stock'],
      assignmentMode: 'none' as const,
    }

    expect(validateChecklistCreateForm({ ...base, flashEnabled: false })).toEqual({ ok: true })
    expect(validateChecklistCreateForm({ ...base, flashEnabled: true })).toEqual({ ok: true })

    expect(
      validateChecklistCreateForm({
        ...base,
        flashEnabled: false,
        businessUnitId: '',
      }),
    ).toMatchObject({
      ok: false,
      openBusinessUnitSheet: true,
    })

    expect(
      validateChecklistCreateForm({
        ...base,
        flashEnabled: false,
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

    expect(
      validateChecklistCreateForm({
        ...base,
        flashEnabled: true,
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
    ).toEqual({ ok: true })
  })
})
