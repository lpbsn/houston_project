import { describe, expect, it } from 'vitest'

import { ActionPlansApiError } from '../api'
import { mapActionPlanApiErrors } from './action-plan-api-error-map'

describe('mapActionPlanApiErrors', () => {
  it('maps confirmed serializer task errors by payload index', () => {
    const error = new ActionPlansApiError({
      status: 400,
      detail: 'Request validation failed.',
      code: 'validation_error',
      errors: {
        title: ['This field is required.'],
        tasks: [{}, { task: ['This field may not be blank.'] }],
      },
    })

    const mapped = mapActionPlanApiErrors(error, {
      payloadTaskIds: ['t-a', 't-b'],
      taskListKey: 'tasks',
    })

    expect(mapped.apiFieldErrors.title).toBe('This field is required.')
    expect(mapped.apiFieldErrors['tasks.t-b.task']).toBe('This field may not be blank.')
    expect(mapped.globalError).toBeNull()
  })

  it('maps pending_tasks for execution edit', () => {
    const error = new ActionPlansApiError({
      status: 400,
      detail: 'Request validation failed.',
      code: 'validation_error',
      errors: {
        pending_tasks: [{ business_unit_id: ['This field is required.'] }],
      },
    })

    const mapped = mapActionPlanApiErrors(error, {
      payloadTaskIds: ['pending-1'],
      taskListKey: 'pending_tasks',
    })

    expect(mapped.apiFieldErrors['tasks.pending-1.businessUnitId']).toBe(
      'This field is required.',
    )
  })

  it('maps first planning item schedule fields', () => {
    const error = new ActionPlansApiError({
      status: 400,
      detail: 'Request validation failed.',
      code: 'validation_error',
      errors: {
        items: [{ end_date: ['This field is required.'], recurrence_days: ['Required.'] }],
      },
    })

    const mapped = mapActionPlanApiErrors(error)
    expect(mapped.apiFieldErrors.endDate).toBe('This field is required.')
    expect(mapped.apiFieldErrors.recurrenceDays).toBe('Required.')
  })

  it('sends service-style errors without errors tree to global', () => {
    const error = new ActionPlansApiError({
      status: 400,
      detail: 'At least one task or assignee is required.',
      code: 'validation_error',
    })

    const mapped = mapActionPlanApiErrors(error)
    expect(mapped.apiFieldErrors).toEqual({})
    expect(mapped.globalError).toBe('At least one task or assignee is required.')
  })

  it('sends unknown error keys to global', () => {
    const error = new ActionPlansApiError({
      status: 400,
      detail: 'Request validation failed.',
      code: 'validation_error',
      errors: {
        mystery_field: ['Nope'],
        non_field_errors: ['Invalid payload.'],
      },
    })

    const mapped = mapActionPlanApiErrors(error)
    expect(mapped.apiFieldErrors).toEqual({})
    expect(mapped.globalError).toBe('Nope')
  })
})
