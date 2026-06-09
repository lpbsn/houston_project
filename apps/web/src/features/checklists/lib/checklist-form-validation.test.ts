import { describe, expect, it } from 'vitest'

import {
  hasAssignmentFormErrors,
  validateAssignmentForm,
  validatePersonalTemplateCreate,
  validateSharedTemplateCreate,
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

  it('requires business unit for shared template create', () => {
    expect(validateSharedTemplateCreate({ title: 'Routine', businessUnitId: '' })).toBeTruthy()
    expect(
      validateSharedTemplateCreate({ title: 'Routine', businessUnitId: 'bu-1' }),
    ).toBeNull()
  })

  it('requires title for personal template create', () => {
    expect(validatePersonalTemplateCreate({ title: '' })).toBeTruthy()
    expect(validatePersonalTemplateCreate({ title: 'Ma routine' })).toBeNull()
  })

  it('requires task', () => {
    expect(validateTask('')).toBe('La tâche est obligatoire.')
    expect(validateTask('Vérifier stock')).toBeNull()
  })
})
