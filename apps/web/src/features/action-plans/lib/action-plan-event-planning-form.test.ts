import { afterEach, describe, expect, it, vi } from 'vitest'

import { createActionPlanAssigneeDraft } from './action-plan-form-validation'
import {
  combineDateAndTimeToIso,
  combineDateTimeToIso,
  createActionPlanEventPlanningDraft,
  formatAssigneeSummary,
  formatDatePillLabel,
  formatRecurrenceDaysSummary,
  formatTimePillLabel,
  getDefaultPlanningTime,
  snapTimeToFiveMinutes,
  splitIsoToDateAndTime,
  toCreateFormPlanningSlice,
  toScheduleDraft,
  toSharedChronologyFields,
  toUseRequestOptions,
  validateActionPlanEventPlanningDraft,
} from './action-plan-event-planning-form'

describe('action-plan-event-planning-form', () => {
  afterEach(() => {
    vi.useRealTimers()
  })
  it('maps all-day one-shot datetimes', () => {
    const draft = {
      ...createActionPlanEventPlanningDraft(),
      allDay: true,
      startDate: '2026-07-01',
      endDate: '2026-07-02',
    }
    const { sharedStartAt, sharedEndAt } = toSharedChronologyFields(draft)
    expect(sharedStartAt).toBeTruthy()
    expect(sharedEndAt).toBeTruthy()
    expect(new Date(sharedStartAt).getDate()).toBe(1)
    expect(new Date(sharedEndAt).getDate()).toBe(2)
  })

  it('maps timed one-shot datetimes', () => {
    const iso = combineDateTimeToIso('2026-07-01', '09:30', 'start')
    expect(iso).toBeTruthy()
    expect(new Date(iso).getHours()).toBe(9)
  })

  it('maps repeat draft to schedule', () => {
    const draft = {
      ...createActionPlanEventPlanningDraft(),
      repeatEnabled: true,
      startDate: '2026-07-01',
      startTime: '09:00',
      endTime: '10:00',
      recurrenceEndDate: '2026-12-31',
      recurrenceDays: ['monday', 'wednesday'] as const,
    }
    const schedule = toScheduleDraft(draft)
    expect(schedule).toEqual({
      enabled: true,
      recurrenceDays: ['monday', 'wednesday'],
      startDate: '2026-07-01',
      endDate: '2026-12-31',
      startAt: '09:00',
      endAt: '10:00',
    })
  })

  it('maps all-day repeat to schedule times', () => {
    const draft = {
      ...createActionPlanEventPlanningDraft(),
      allDay: true,
      repeatEnabled: true,
      startDate: '2026-07-01',
      recurrenceEndDate: '2026-12-31',
      recurrenceDays: ['friday'] as const,
    }
    const schedule = toScheduleDraft(draft)
    expect(schedule.startAt).toBe('00:00')
    expect(schedule.endAt).toBe('23:59')
  })

  it('builds create form slice with per-assignee chronology flag', () => {
    const draft = {
      ...createActionPlanEventPlanningDraft(),
      usePerAssigneeChronology: true,
      assignees: [createActionPlanAssigneeDraft({ membershipId: 'm1', businessUnitId: 'bu1' })],
    }
    const slice = toCreateFormPlanningSlice(draft)
    expect(slice.useSharedChronology).toBe(false)
    expect(slice.sharedVisibleFrom).toBe('')
  })

  it('builds use request options', () => {
    const draft = {
      ...createActionPlanEventPlanningDraft(),
      startDate: '2026-07-01',
      startTime: '08:00',
      endDate: '2026-07-01',
      endTime: '09:00',
    }
    const options = toUseRequestOptions(draft)
    expect(options.useSharedChronology).toBe(true)
    expect(options.sharedStartAt).toBeTruthy()
    expect(options.sharedEndAt).toBeTruthy()
  })

  it('formats assignee summary', () => {
    expect(formatAssigneeSummary([], { staffMode: true, staffDisplayName: 'Alice' })).toBe('Alice')
    expect(
      formatAssigneeSummary([
        createActionPlanAssigneeDraft({ membershipId: 'm1', displayName: 'Bob' }),
        createActionPlanAssigneeDraft({ membershipId: 'm2', displayName: 'Carol' }),
      ]),
    ).toBe('2 assignés')
  })

  it('formats recurrence days summary', () => {
    expect(formatRecurrenceDaysSummary(['monday', 'wednesday'])).toBe('Lundi, Mercredi')
  })

  it('validates repeat requirements', () => {
    const errors = validateActionPlanEventPlanningDraft(
      { ...createActionPlanEventPlanningDraft(), repeatEnabled: true },
      { allowRepeat: true },
    )
    expect(errors.recurrenceDays).toBeTruthy()
    expect(errors.recurrenceEndDate).toBeTruthy()
  })

  it('rejects repeat when not allowed', () => {
    const errors = validateActionPlanEventPlanningDraft(
      { ...createActionPlanEventPlanningDraft(), repeatEnabled: true },
      { allowRepeat: false },
    )
    expect(errors.repeatEnabled).toBeTruthy()
  })

  it('snaps times to five-minute increments', () => {
    expect(snapTimeToFiveMinutes('09:02')).toBe('09:00')
    expect(snapTimeToFiveMinutes('09:03')).toBe('09:05')
    expect(snapTimeToFiveMinutes('23:58')).toBe('00:00')
  })

  it('defaults planning time to the current local time snapped to five minutes', () => {
    vi.setSystemTime(new Date(2026, 6, 8, 14, 32, 0))
    expect(getDefaultPlanningTime()).toBe('14:30')

    vi.setSystemTime(new Date(2026, 6, 8, 14, 33, 0))
    expect(getDefaultPlanningTime()).toBe('14:35')

    vi.setSystemTime(new Date(2026, 6, 8, 23, 58, 0))
    expect(getDefaultPlanningTime()).toBe('00:00')
  })

  it('formats time pill labels in 24h', () => {
    expect(formatTimePillLabel('14:30')).toBe('14:30')
    expect(formatTimePillLabel('')).toBe('—')
    expect(formatTimePillLabel('09:07')).toBe('09:05')
  })

  it('formats date pill labels', () => {
    expect(formatDatePillLabel('2026-07-04')).toContain('2026')
    expect(formatDatePillLabel('')).toBe('—')
  })

  it('splits and combines ISO date/time in local fields', () => {
    const iso = combineDateTimeToIso('2026-07-01', '09:30', 'start')
    const parts = splitIsoToDateAndTime(iso)
    expect(parts.date).toBe('2026-07-01')
    expect(parts.time).toBe('09:30')
    expect(combineDateAndTimeToIso(parts.date, parts.time, 'start')).toBe(iso)
  })
})
