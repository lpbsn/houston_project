import { afterEach, describe, expect, it, vi } from 'vitest'

import { createActionPlanAssigneeDraft } from './action-plan-form-validation'
import {
  buildScheduleRequestForAssignee,
  buildScheduleRequestsFromDraft,
  buildUseRequestForAssignee,
  combineDateAndTimeToIso,
  combineDateTimeToIso,
  createActionPlanEventPlanningDraft,
  formatAssigneeSummary,
  formatDatePillLabel,
  formatRecurrenceDaysSummary,
  formatTimePillLabel,
  getDefaultPlanningTime,
  hasGlobalRepeat,
  hasPerAssigneeRepeat,
  resolveNowStartForPlanning,
  shouldHidePrimaryPlanningActions,
  snapTimeToFiveMinutes,
  splitIsoToDateAndTime,
  toCreateFormPlanningSlice,
  toScheduleDraft,
  toSharedChronologyFields,
  toUseRequestOptions,
  validateActionPlanEventPlanningDraft,
  validateAssigneePlanningAction,
  validatePerAssigneePlanningDraft,
} from './action-plan-event-planning-form'

describe('action-plan-event-planning-form', () => {
  afterEach(() => {
    vi.useRealTimers()
  })

  it('maps timed one-shot datetimes', () => {
    const draft = {
      ...createActionPlanEventPlanningDraft(),
      startDate: '2026-07-01',
      startTime: '09:00',
      endDate: '2026-07-02',
      endTime: '10:00',
    }
    const { sharedStartAt, sharedEndAt } = toSharedChronologyFields(draft)
    expect(sharedStartAt).toBeTruthy()
    expect(sharedEndAt).toBeTruthy()
    expect(new Date(sharedStartAt).getDate()).toBe(1)
    expect(new Date(sharedEndAt).getDate()).toBe(2)
  })

  it('maps timed one-shot datetimes from combine helper', () => {
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

  it('resolves now start with five-minute snap and day rollover', () => {
    vi.setSystemTime(new Date(2026, 6, 19, 10, 2, 0))
    expect(resolveNowStartForPlanning()).toEqual({
      date: '2026-07-19',
      time: '10:00',
    })

    vi.setSystemTime(new Date(2026, 6, 19, 10, 3, 0))
    expect(resolveNowStartForPlanning()).toEqual({
      date: '2026-07-19',
      time: '10:05',
    })

    vi.setSystemTime(new Date(2026, 6, 19, 23, 58, 0))
    expect(resolveNowStartForPlanning()).toEqual({
      date: '2026-07-20',
      time: '00:00',
    })
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
    expect(formatTimePillLabel('')).toBe('HH:MM')
    expect(formatTimePillLabel('09:07')).toBe('09:05')
  })

  it('formats date pill labels', () => {
    expect(formatDatePillLabel('2026-07-04')).toContain('2026')
    expect(formatDatePillLabel('')).toBe('JJ/MM/AAAA')
  })

  it('splits and combines ISO date/time in local fields', () => {
    const iso = combineDateTimeToIso('2026-07-01', '09:30', 'start')
    const parts = splitIsoToDateAndTime(iso)
    expect(parts.date).toBe('2026-07-01')
    expect(parts.time).toBe('09:30')
    expect(combineDateAndTimeToIso(parts.date, parts.time, 'start')).toBe(iso)
  })

  it('detects global vs per-assignee repeat modes', () => {
    const globalDraft = {
      ...createActionPlanEventPlanningDraft(),
      repeatEnabled: true,
      usePerAssigneeChronology: false,
    }
    const perAssigneeDraft = {
      ...createActionPlanEventPlanningDraft(),
      usePerAssigneeChronology: true,
      assignees: [
        createActionPlanAssigneeDraft({
          membershipId: 'm1',
          businessUnitId: 'bu1',
          repeatEnabled: true,
        }),
      ],
    }

    expect(hasGlobalRepeat(globalDraft)).toBe(true)
    expect(hasPerAssigneeRepeat(globalDraft)).toBe(false)
    expect(shouldHidePrimaryPlanningActions(perAssigneeDraft)).toBe(true)
    expect(hasPerAssigneeRepeat(perAssigneeDraft)).toBe(true)
  })

  it('builds one schedule per repeating assignee with start date from assignee card', () => {
    const draft = {
      ...createActionPlanEventPlanningDraft(),
      usePerAssigneeChronology: true,
      assignees: [
        createActionPlanAssigneeDraft({
          membershipId: 'm1',
          businessUnitId: 'bu1',
          startAt: combineDateAndTimeToIso('2026-07-01', '09:00', 'start'),
          endAt: combineDateAndTimeToIso('2026-07-01', '10:00', 'end'),
          repeatEnabled: true,
          recurrenceDays: ['monday'],
          recurrenceEndDate: '2026-12-31',
        }),
        createActionPlanAssigneeDraft({
          membershipId: 'm2',
          businessUnitId: 'bu1',
          startAt: combineDateAndTimeToIso('2026-08-01', '14:00', 'start'),
          endAt: combineDateAndTimeToIso('2026-08-01', '15:00', 'end'),
          repeatEnabled: true,
          recurrenceDays: ['friday'],
          recurrenceEndDate: '2026-12-31',
        }),
      ],
    }

    const schedules = buildScheduleRequestsFromDraft(draft)
    expect(schedules).toHaveLength(2)
    expect(schedules[0]?.start_date).toBe('2026-07-01')
    expect(schedules[1]?.start_date).toBe('2026-08-01')
    expect(schedules[0]?.recurrence_days).toEqual(['monday'])
    expect(schedules[1]?.recurrence_days).toEqual(['friday'])
    expect(schedules[0]?.use_shared_chronology).toBe(false)
    expect(schedules[1]?.use_shared_chronology).toBe(false)
  })

  it('builds use request for assignee with independent start and end dates', () => {
    const assignee = createActionPlanAssigneeDraft({
      membershipId: 'm1',
      businessUnitId: 'bu1',
      startAt: combineDateAndTimeToIso('2026-07-04', '22:00', 'start'),
      endAt: combineDateAndTimeToIso('2026-07-05', '06:00', 'end'),
    })
    const draft = {
      ...createActionPlanEventPlanningDraft(),
      usePerAssigneeChronology: true,
      assignees: [assignee],
    }

    const body = buildUseRequestForAssignee(draft, assignee)
    expect(body?.assignees?.[0]?.start_at).toBeTruthy()
    expect(body?.assignees?.[0]?.end_at).toBeTruthy()
    expect(Date.parse(body!.assignees![0]!.end_at!)).toBeGreaterThan(
      Date.parse(body!.assignees![0]!.start_at!),
    )
    expect(splitIsoToDateAndTime(body!.assignees![0]!.start_at!).date).toBe('2026-07-04')
    expect(splitIsoToDateAndTime(body!.assignees![0]!.end_at!).date).toBe('2026-07-05')
  })

  it('validates per-assignee repeat requirements from assignee card fields', () => {
    const assignee = createActionPlanAssigneeDraft({
      membershipId: 'm1',
      businessUnitId: 'bu1',
      repeatEnabled: true,
      startAt: combineDateAndTimeToIso('2026-07-01', '09:00', 'start'),
      endAt: combineDateAndTimeToIso('2026-07-01', '10:00', 'end'),
    })
    const draft = {
      ...createActionPlanEventPlanningDraft(),
      usePerAssigneeChronology: true,
      assignees: [assignee],
    }

    const errors = validateAssigneePlanningAction(draft, assignee.id, {
      allowRepeat: true,
      action: 'schedule',
    })
    expect(errors[`assignee.${assignee.id}.recurrenceDays`]).toBeTruthy()
    expect(errors[`assignee.${assignee.id}.recurrenceEndDate`]).toBeTruthy()
    expect(errors.startDate).toBeUndefined()
  })

  it('rejects per-assignee launch when end is before start', () => {
    const assignee = createActionPlanAssigneeDraft({
      membershipId: 'm1',
      businessUnitId: 'bu1',
      startAt: combineDateAndTimeToIso('2026-07-05', '09:00', 'start'),
      endAt: combineDateAndTimeToIso('2026-07-04', '10:00', 'end'),
    })
    const draft = {
      ...createActionPlanEventPlanningDraft(),
      usePerAssigneeChronology: true,
      assignees: [assignee],
    }

    const errors = validateAssigneePlanningAction(draft, assignee.id, { action: 'launch' })
    expect(errors[`assignee.${assignee.id}.endDate`]).toBeTruthy()
  })

  it('uses assignee start date in schedule request', () => {
    const assignee = createActionPlanAssigneeDraft({
      membershipId: 'm1',
      businessUnitId: 'bu1',
      startAt: combineDateAndTimeToIso('2026-07-10', '08:00', 'start'),
      endAt: combineDateAndTimeToIso('2026-07-10', '09:00', 'end'),
      repeatEnabled: true,
      recurrenceDays: ['tuesday'],
      recurrenceEndDate: '2026-12-31',
    })
    const body = buildScheduleRequestForAssignee(createActionPlanEventPlanningDraft(), assignee)
    expect(body?.start_date).toBe('2026-07-10')
  })

  it('skips global repeat validation when per-assignee chronology is enabled', () => {
    const errors = validateActionPlanEventPlanningDraft(
      {
        ...createActionPlanEventPlanningDraft(),
        repeatEnabled: true,
        usePerAssigneeChronology: true,
      },
      { allowRepeat: true },
    )
    expect(errors.recurrenceDays).toBeUndefined()
  })

  it('aggregates per-assignee validation errors for mixed recurring and one-shot assignees', () => {
    const recurringAssignee = createActionPlanAssigneeDraft({
      id: 'recurring',
      membershipId: 'm1',
      businessUnitId: 'bu1',
      repeatEnabled: true,
      startAt: combineDateAndTimeToIso('2026-07-12', '05:00', 'start'),
      endAt: combineDateAndTimeToIso('2026-07-12', '16:05', 'end'),
    })
    const oneShotAssignee = createActionPlanAssigneeDraft({
      id: 'one-shot',
      membershipId: 'm2',
      businessUnitId: 'bu1',
      repeatEnabled: false,
      startAt: combineDateAndTimeToIso('2026-07-11', '05:00', 'start'),
      endAt: combineDateAndTimeToIso('2026-07-25', '08:00', 'end'),
    })
    const draft = {
      ...createActionPlanEventPlanningDraft(),
      usePerAssigneeChronology: true,
      assignees: [recurringAssignee, oneShotAssignee],
    }

    const errors = validatePerAssigneePlanningDraft(draft, { allowRepeat: true })
    expect(errors[`assignee.${recurringAssignee.id}.recurrenceDays`]).toBeTruthy()
    expect(errors[`assignee.${recurringAssignee.id}.recurrenceEndDate`]).toBeTruthy()
    expect(errors[`assignee.${oneShotAssignee.id}.startDate`]).toBeUndefined()
  })

  it('returns no errors when all per-assignee cards are complete', () => {
    const recurringAssignee = createActionPlanAssigneeDraft({
      membershipId: 'm1',
      businessUnitId: 'bu1',
      repeatEnabled: true,
      startAt: combineDateAndTimeToIso('2026-07-12', '05:00', 'start'),
      endAt: combineDateAndTimeToIso('2026-07-12', '16:05', 'end'),
      recurrenceDays: ['tuesday', 'thursday', 'saturday'],
      recurrenceEndDate: '2026-07-25',
    })
    const oneShotAssignee = createActionPlanAssigneeDraft({
      membershipId: 'm2',
      businessUnitId: 'bu1',
      repeatEnabled: false,
      startAt: combineDateAndTimeToIso('2026-07-11', '05:00', 'start'),
      endAt: combineDateAndTimeToIso('2026-07-25', '08:00', 'end'),
    })
    const draft = {
      ...createActionPlanEventPlanningDraft(),
      usePerAssigneeChronology: true,
      assignees: [recurringAssignee, oneShotAssignee],
    }

    expect(validatePerAssigneePlanningDraft(draft, { allowRepeat: true })).toEqual({})
  })

  it('requires at least one assignee when per-assignee chronology is enabled', () => {
    const errors = validatePerAssigneePlanningDraft(
      {
        ...createActionPlanEventPlanningDraft(),
        usePerAssigneeChronology: true,
        assignees: [],
      },
      { allowRepeat: true },
    )

    expect(errors.assignees).toBe('Ajoutez au moins un assigné pour lancer le plan.')
  })
})
