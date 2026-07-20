import { describe, expect, it, vi } from 'vitest'

import { createActionPlanAssigneeDraft } from './action-plan-form-validation'
import {
  CATALOG_LAUNCH_EXECUTION_LABEL,
  formatPlanningSubmitFeedback,
  isCatalogPlanningPrimaryDisabled,
  resolveCatalogPlanningSubmit,
  resolveCatalogPlanningSubmitFallbackMessage,
  validateCatalogPlanningDraft,
} from './action-plan-catalog-planning-submit'
import {
  combineDateAndTimeToIso,
  createActionPlanEventPlanningDraft,
} from './action-plan-event-planning-form'
import { ActionPlansApiError } from '../api'

describe('action-plan-catalog-planning-submit', () => {
  it('exposes static launch execution label for catalog UI', () => {
    expect(CATALOG_LAUNCH_EXECUTION_LABEL).toBe("Lancer l'exécution")
  })

  it('resolves global repeat as planning schedule item', () => {
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
    expect(submit?.kind).toBe('planning')
    expect(submit?.body.use_shared_chronology).toBe(true)
    expect(submit?.body.items).toHaveLength(1)
    expect(submit?.body.items[0]).toEqual(
      expect.objectContaining({
        kind: 'schedule',
        recurrence_days: ['monday'],
      }),
    )
  })

  it('resolves per-assignee all one-shot as N planning execution items', () => {
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
    expect(submit?.kind).toBe('planning')
    expect(submit?.body.use_shared_chronology).toBe(false)
    expect(submit?.body.items).toHaveLength(2)
    expect(submit?.body.items.map((item) => item.kind)).toEqual(['execution', 'execution'])
    expect(submit?.body.items[0]).toEqual(
      expect.objectContaining({
        primary_membership_id: 'm1',
        kind: 'execution',
      }),
    )
    expect(submit?.body.items[1]).toEqual(
      expect.objectContaining({
        primary_membership_id: 'm2',
        kind: 'execution',
      }),
    )
  })

  it('resolves per-assignee mixed assignees as planning schedule + execution items', () => {
    const recurringAssignee = createActionPlanAssigneeDraft({
      membershipId: 'm1',
      businessUnitId: 'bu1',
      repeatEnabled: true,
      startAt: composeDateTime('2026-07-12', '05:00'),
      endAt: composeDateTime('2026-07-12', '16:05'),
      recurrenceDays: ['tuesday', 'thursday', 'saturday'],
      recurrenceEndDate: '2026-07-25',
    })
    const oneShotAssignee = createActionPlanAssigneeDraft({
      membershipId: 'm2',
      businessUnitId: 'bu1',
      repeatEnabled: false,
      startAt: composeDateTime('2026-07-11', '05:00'),
      endAt: composeDateTime('2026-07-25', '08:00'),
    })
    const draft = {
      ...createActionPlanEventPlanningDraft(),
      usePerAssigneeChronology: true,
      assignees: [recurringAssignee, oneShotAssignee],
    }

    const submit = resolveCatalogPlanningSubmit(draft, { canSchedule: true })
    expect(submit?.kind).toBe('planning')
    expect(submit?.body.use_shared_chronology).toBe(false)
    expect(submit?.body.items).toHaveLength(2)
    expect(submit?.body.items.map((item) => item.kind).sort()).toEqual([
      'execution',
      'schedule',
    ])
  })

  it('allows distinct per-assignee recurrence patterns', () => {
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
    expect(errors.assignees).toBeUndefined()
    const submit = resolveCatalogPlanningSubmit(draft, { canSchedule: true })
    expect(submit?.body.items).toHaveLength(2)
    expect(submit?.body.items.every((item) => item.kind === 'schedule')).toBe(true)
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

  it('formats planning submit feedback as X planifications et Y exécutions', () => {
    expect(
      formatPlanningSubmitFeedback({ schedules_created: 2, executions_created: 3 }),
    ).toBe('2 planifications et 3 exécutions ont été créées.')
  })

  it('maps planning fallback messages', () => {
    const submit = {
      kind: 'planning' as const,
      body: {
        submission_id: 'sub-1',
        use_shared_chronology: true,
        items: [],
      },
    }

    expect(resolveCatalogPlanningSubmitFallbackMessage(submit)).toBe(
      'Le plan n’a pas pu être utilisé.',
    )
    expect(
      resolveCatalogPlanningSubmitFallbackMessage(
        submit,
        new ActionPlansApiError({
          status: 400,
          detail: 'Use failed.',
          code: 'validation_error',
        }),
      ),
    ).toBe('Use failed.')
  })
})

function composeDateTime(date: string, time: string): string {
  return combineDateAndTimeToIso(date, time, 'start')
}
