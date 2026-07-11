import { describe, expect, it } from 'vitest'

import { createActionPlanAssigneeDraft } from './action-plan-form-validation'
import {
  buildPerAssigneeScheduleFromDraft,
  isCatalogPlanningPrimaryDisabled,
  resolveCatalogPlanningPrimaryLabel,
  resolveCatalogPlanningSubmit,
  validateCatalogPlanningDraft,
} from './action-plan-catalog-planning-submit'
import {
  combineDateAndTimeToIso,
  createActionPlanEventPlanningDraft,
} from './action-plan-event-planning-form'

describe('action-plan-catalog-planning-submit', () => {
  it('resolves global repeat as schedule-only submit', () => {
    const draft = {
      ...createActionPlanEventPlanningDraft(),
      repeatEnabled: true,
      startDate: '2026-07-01',
      startTime: '09:00',
      endTime: '10:00',
      recurrenceEndDate: '2026-12-31',
      recurrenceDays: ['monday'] as const,
      assignees: [
        createActionPlanAssigneeDraft({
          membershipId: 'm1',
          businessUnitId: 'bu1',
        }),
      ],
    }

    const submit = resolveCatalogPlanningSubmit(draft, { canSchedule: true })
    expect(submit?.kind).toBe('schedule')
    if (submit?.kind === 'schedule') {
      expect(submit.scheduleBody.recurrence_days).toEqual(['monday'])
      expect(submit.scheduleBody.use_shared_chronology).toBe(true)
    }
  })

  it('resolves per-assignee all one-shot as use-only submit', () => {
    const draft = {
      ...createActionPlanEventPlanningDraft(),
      usePerAssigneeChronology: true,
      assignees: [
        createActionPlanAssigneeDraft({
          membershipId: 'm1',
          businessUnitId: 'bu1',
          startAt: combineDateAndTimeToIso('2026-07-01', '09:00', 'start'),
          endAt: combineDateAndTimeToIso('2026-07-01', '10:00', 'end'),
        }),
        createActionPlanAssigneeDraft({
          membershipId: 'm2',
          businessUnitId: 'bu1',
          startAt: combineDateAndTimeToIso('2026-07-02', '14:00', 'start'),
          endAt: combineDateAndTimeToIso('2026-07-02', '15:00', 'end'),
        }),
      ],
    }

    const submit = resolveCatalogPlanningSubmit(draft, { canSchedule: true })
    expect(submit?.kind).toBe('use')
    if (submit?.kind === 'use') {
      expect(submit.useBody.use_shared_chronology).toBe(false)
      expect(submit.useBody.assignees).toHaveLength(2)
    }
    expect(resolveCatalogPlanningPrimaryLabel(draft, { canSchedule: true })).toBe(
      "Lancer l'exécution",
    )
  })

  it('resolves per-assignee all repeat as schedule-only submit', () => {
    const draft = {
      ...createActionPlanEventPlanningDraft(),
      usePerAssigneeChronology: true,
      assignees: [
        createActionPlanAssigneeDraft({
          membershipId: 'm1',
          businessUnitId: 'bu1',
          repeatEnabled: true,
          startAt: combineDateAndTimeToIso('2026-07-12', '05:00', 'start'),
          endAt: combineDateAndTimeToIso('2026-07-12', '16:05', 'end'),
          recurrenceDays: ['tuesday', 'thursday'],
          recurrenceEndDate: '2026-07-25',
        }),
      ],
    }

    const submit = resolveCatalogPlanningSubmit(draft, { canSchedule: true })
    expect(submit?.kind).toBe('schedule')
    if (submit?.kind === 'schedule') {
      expect(submit.scheduleBody.use_shared_chronology).toBe(false)
      expect(submit.scheduleBody.assignees).toHaveLength(1)
    }
    expect(resolveCatalogPlanningPrimaryLabel(draft, { canSchedule: true })).toBe(
      'Planifier la récurrence',
    )
  })

  it('resolves per-assignee mixed assignees as mixed submit', () => {
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

    const submit = resolveCatalogPlanningSubmit(draft, { canSchedule: true })
    expect(submit?.kind).toBe('mixed')
    if (submit?.kind === 'mixed') {
      expect(submit.scheduleBody.assignees).toHaveLength(1)
      expect(submit.useBody.assignees).toHaveLength(1)
      expect(submit.useBody.assignees?.[0]?.membership_id).toBe('m2')
    }
    expect(resolveCatalogPlanningPrimaryLabel(draft, { canSchedule: true })).toBe(
      "Lancer l'exécution",
    )
  })

  it('builds grouped per-assignee schedule from draft', () => {
    const draft = {
      ...createActionPlanEventPlanningDraft(),
      usePerAssigneeChronology: true,
      assignees: [
        createActionPlanAssigneeDraft({
          membershipId: 'm1',
          businessUnitId: 'bu1',
          repeatEnabled: true,
          startAt: combineDateAndTimeToIso('2026-07-12', '05:00', 'start'),
          endAt: combineDateAndTimeToIso('2026-07-12', '16:05', 'end'),
          recurrenceDays: ['tuesday'],
          recurrenceEndDate: '2026-07-25',
        }),
        createActionPlanAssigneeDraft({
          membershipId: 'm2',
          businessUnitId: 'bu1',
          repeatEnabled: true,
          startAt: combineDateAndTimeToIso('2026-07-12', '06:00', 'start'),
          endAt: combineDateAndTimeToIso('2026-07-12', '17:00', 'end'),
          recurrenceDays: ['tuesday'],
          recurrenceEndDate: '2026-07-25',
        }),
      ],
    }

    const schedule = buildPerAssigneeScheduleFromDraft(draft)
    expect(schedule?.assignees).toHaveLength(2)
    expect(schedule?.recurrence_days).toEqual(['tuesday'])
  })

  it('validates per-assignee draft with compatible repeats requirement', () => {
    const draft = {
      ...createActionPlanEventPlanningDraft(),
      usePerAssigneeChronology: true,
      assignees: [
        createActionPlanAssigneeDraft({
          membershipId: 'm1',
          businessUnitId: 'bu1',
          repeatEnabled: true,
          startAt: combineDateAndTimeToIso('2026-07-01', '09:00', 'start'),
          endAt: combineDateAndTimeToIso('2026-07-01', '10:00', 'end'),
          recurrenceDays: ['monday'],
          recurrenceEndDate: '2026-12-31',
        }),
        createActionPlanAssigneeDraft({
          membershipId: 'm2',
          businessUnitId: 'bu1',
          repeatEnabled: true,
          startAt: combineDateAndTimeToIso('2026-08-01', '09:00', 'start'),
          endAt: combineDateAndTimeToIso('2026-08-01', '10:00', 'end'),
          recurrenceDays: ['friday'],
          recurrenceEndDate: '2026-12-31',
        }),
      ],
    }

    const errors = validateCatalogPlanningDraft(draft, { canSchedule: true })
    expect(errors.assignees).toBe(
      'Les récurrences doivent partager les mêmes dates et jours pour être créées ensemble.',
    )
  })

  it('disables primary action for incomplete global repeat schedule', () => {
    const draft = {
      ...createActionPlanEventPlanningDraft(),
      repeatEnabled: true,
      recurrenceDays: ['monday'] as const,
    }

    expect(
      isCatalogPlanningPrimaryDisabled(draft, { canSchedule: true, isPending: false }),
    ).toBe(true)
    expect(
      isCatalogPlanningPrimaryDisabled(draft, { canSchedule: true, isPending: true }),
    ).toBe(true)
  })
})
