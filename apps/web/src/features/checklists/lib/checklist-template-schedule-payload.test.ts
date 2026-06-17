import { describe, expect, it } from 'vitest'

import { buildChecklistTemplateSchedulePayload } from './checklist-template-schedule-payload'

describe('buildChecklistTemplateSchedulePayload', () => {
  it('builds one-shot execution payload without start_date or recurrence', () => {
    expect(
      buildChecklistTemplateSchedulePayload({
        assignedTo: 'member-1',
        startAt: '09:30',
        endAt: '10:45',
        recurrenceDays: [],
        recurrenceEndDate: '',
      }),
    ).toEqual({
      assigned_to: 'member-1',
      start_at: '09:30:00',
      end_at: '10:45:00',
    })
  })

  it('builds recurring assignment payload with recurrence_end_date', () => {
    expect(
      buildChecklistTemplateSchedulePayload({
        assignedTo: 'member-1',
        startAt: '08:00',
        endAt: '09:00',
        recurrenceDays: ['monday', 'friday'],
        recurrenceEndDate: '2026-06-30',
      }),
    ).toEqual({
      assigned_to: 'member-1',
      start_at: '08:00:00',
      end_at: '09:00:00',
      recurrence_days: ['monday', 'friday'],
      recurrence_end_date: '2026-06-30',
    })
  })
})
