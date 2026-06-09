import { describe, expect, it } from 'vitest'

import type { ChecklistAssignment } from '@/features/checklists/types'

import {
  assignmentToFormValues,
  buildChecklistAssignmentCreatePayload,
  buildChecklistAssignmentUpdatePayload,
  toApiTime,
  toFormTime,
} from './checklist-assignment-create-payload'

describe('toApiTime', () => {
  it('converts HH:MM to HH:MM:SS', () => {
    expect(toApiTime('10:00')).toBe('10:00:00')
  })
})

describe('buildChecklistAssignmentCreatePayload', () => {
  it('maps form values to API payload', () => {
    const payload = buildChecklistAssignmentCreatePayload({
      assignedTo: 'member-uuid-1',
      startDate: '2026-06-09',
      endDate: '2026-06-19',
      startAt: '10:00',
      endAt: '11:00',
      recurrenceDays: ['monday', 'wednesday'],
    })

    expect(payload.assigned_to).toBe('member-uuid-1')
    expect(payload.start_date).toBe('2026-06-09')
    expect(payload.end_date).toBe('2026-06-19')
    expect(payload.start_at).toBe('10:00:00')
    expect(payload.end_at).toBe('11:00:00')
    expect(payload.recurrence_days).toEqual(['monday', 'wednesday'])
  })

  it('sets recurrence_days to null and end_date to start_date for one-shot', () => {
    const payload = buildChecklistAssignmentCreatePayload({
      assignedTo: 'member-uuid-1',
      startDate: '2026-06-10',
      endDate: '2026-06-20',
      startAt: '10:00',
      endAt: '12:00',
      recurrenceDays: [],
    })

    expect(payload.recurrence_days).toBeNull()
    expect(payload.end_date).toBe('2026-06-10')
  })
})

describe('buildChecklistAssignmentUpdatePayload', () => {
  it('maps form values to PATCH payload', () => {
    const payload = buildChecklistAssignmentUpdatePayload({
      assignedTo: 'member-uuid-2',
      startDate: '2026-06-11',
      endDate: '2026-06-21',
      startAt: '09:00',
      endAt: '11:00',
      recurrenceDays: ['friday'],
    })

    expect(payload.assigned_to).toBe('member-uuid-2')
    expect(payload.recurrence_days).toEqual(['friday'])
  })
})

describe('assignmentToFormValues', () => {
  it('prefills date and time values from assignment', () => {
    const assignment = {
      assigned_to_id: 'member-uuid-1',
      start_date: '2026-06-10',
      end_date: '2026-06-20',
      start_at: '08:00:00',
      end_at: '10:00:00',
      recurrence_days: ['monday'],
    } as ChecklistAssignment

    const values = assignmentToFormValues(assignment)

    expect(values.assignedTo).toBe('member-uuid-1')
    expect(values.startDate).toBe('2026-06-10')
    expect(values.endDate).toBe('2026-06-20')
    expect(values.startAt).toBe(toFormTime(assignment.start_at))
    expect(values.endAt).toBe(toFormTime(assignment.end_at))
    expect(values.recurrenceDays).toEqual(['monday'])
  })
})
