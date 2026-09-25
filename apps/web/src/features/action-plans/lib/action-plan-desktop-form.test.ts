import { describe, expect, it } from 'vitest'

import { createActionPlanAssigneeDraft } from './action-plan-form-validation'
import {
  ACTION_PLAN_DESKTOP_SAVE_LABEL,
  ACTION_PLAN_DESKTOP_SCHEDULE_LABEL,
  ACTION_PLAN_DESKTOP_START_LABEL,
  formatActionPlanSubmissionNotice,
  resolveActionPlanDesktopJourneyTitle,
  resolveDesktopLaunchLabel,
  resolveDesktopLibraryPersistence,
  summarizeDirectCreateLaunch,
} from './action-plan-desktop-form'
import { createActionPlanEventPlanningDraft } from './action-plan-event-planning-form'

const NOW = new Date('2026-09-25T08:00:00.000Z')

function assignee(membershipId: string, partial: Parameters<typeof createActionPlanAssigneeDraft>[0] = {}) {
  return createActionPlanAssigneeDraft({
    membershipId,
    businessUnitId: 'bu-1',
    ...partial,
  })
}

describe('action plan desktop form', () => {
  it('names each entry and locks the library outcome on desktop web', () => {
    expect(resolveActionPlanDesktopJourneyTitle('catalog')).toBe('Créer un modèle')
    expect(resolveActionPlanDesktopJourneyTitle('execution')).toBe('Créer une exécution')
    expect(resolveActionPlanDesktopJourneyTitle('signal-linked')).toBe(
      'Exécution liée à l’observation',
    )
    expect(resolveDesktopLibraryPersistence('catalog', false, true)).toBe(true)
    expect(resolveDesktopLibraryPersistence('execution', true, true)).toBe(false)
    expect(resolveDesktopLibraryPersistence('signal-linked', true, true)).toBe(false)
    expect(resolveDesktopLibraryPersistence('catalog', true, false)).toBe(true)
    expect(resolveDesktopLibraryPersistence('execution', true, false)).toBe(true)
    expect(ACTION_PLAN_DESKTOP_SAVE_LABEL).toBe('Enregistrer')
  })

  it('labels an immediate start as Démarrer', () => {
    const empty = createActionPlanEventPlanningDraft()
    const outcome = summarizeDirectCreateLaunch(empty, { saveToLibrary: false, staffMode: false }, NOW)
    expect(outcome).toEqual({ executions: 1, schedules: 0, hasFutureStart: false })
    expect(resolveDesktopLaunchLabel(outcome)).toBe(ACTION_PLAN_DESKTOP_START_LABEL)
    expect(formatActionPlanSubmissionNotice(outcome)).toBeNull()

    const snappedNow = {
      ...createActionPlanEventPlanningDraft(),
      usePerAssigneeChronology: true,
      assignees: [assignee('m-1', { startAt: new Date(NOW.getTime() + 2 * 60 * 1000).toISOString() })],
    }
    expect(
      resolveDesktopLaunchLabel(
        summarizeDirectCreateLaunch(snappedNow, { saveToLibrary: false, staffMode: false }, NOW),
      ),
    ).toBe(ACTION_PLAN_DESKTOP_START_LABEL)
  })

  it('labels a future one-shot as Programmer', () => {
    const future = {
      ...createActionPlanEventPlanningDraft(),
      startDate: '2099-01-01',
      startTime: '09:00',
    }
    const outcome = summarizeDirectCreateLaunch(future, { saveToLibrary: false, staffMode: false }, NOW)
    expect(outcome).toMatchObject({ executions: 1, schedules: 0, hasFutureStart: true })
    expect(resolveDesktopLaunchLabel(outcome)).toBe(ACTION_PLAN_DESKTOP_SCHEDULE_LABEL)
    expect(formatActionPlanSubmissionNotice(outcome)).toBeNull()
  })

  it('labels a recurrence as Programmer', () => {
    const repeating = { ...createActionPlanEventPlanningDraft(), repeatEnabled: true }
    const outcome = summarizeDirectCreateLaunch(
      repeating,
      { saveToLibrary: false, staffMode: false },
      NOW,
    )
    expect(outcome).toEqual({ executions: 0, schedules: 1, hasFutureStart: false })
    expect(resolveDesktopLaunchLabel(outcome)).toBe(ACTION_PLAN_DESKTOP_SCHEDULE_LABEL)
    expect(formatActionPlanSubmissionNotice(outcome)).toBeNull()
  })

  it('announces the executions and schedules produced by mixed assignee chronologies', () => {
    const mixed = {
      ...createActionPlanEventPlanningDraft(),
      usePerAssigneeChronology: true,
      assignees: [
        assignee('m-1'),
        assignee('m-2', { repeatEnabled: true, recurrenceDays: ['monday'] }),
      ],
    }
    const outcome = summarizeDirectCreateLaunch(mixed, { saveToLibrary: false, staffMode: false }, NOW)
    expect(outcome).toEqual({ executions: 1, schedules: 1, hasFutureStart: false })
    expect(resolveDesktopLaunchLabel(outcome)).toBe(ACTION_PLAN_DESKTOP_SCHEDULE_LABEL)
    expect(formatActionPlanSubmissionNotice(outcome)).toBe(
      'Cette validation créera 1 exécution et 1 planification.',
    )

    const splitTiming = {
      ...createActionPlanEventPlanningDraft(),
      usePerAssigneeChronology: true,
      assignees: [assignee('m-1'), assignee('m-2', { startAt: '2099-01-01T09:00:00.000Z' })],
    }
    const split = summarizeDirectCreateLaunch(
      splitTiming,
      { saveToLibrary: false, staffMode: false },
      NOW,
    )
    expect(split).toEqual({ executions: 2, schedules: 0, hasFutureStart: true })
    expect(resolveDesktopLaunchLabel(split)).toBe(ACTION_PLAN_DESKTOP_SCHEDULE_LABEL)
    expect(formatActionPlanSubmissionNotice(split)).toBe('Cette validation créera 2 exécutions.')

    const severalNow = {
      ...createActionPlanEventPlanningDraft(),
      usePerAssigneeChronology: true,
      assignees: [assignee('m-1'), assignee('m-2')],
    }
    const several = summarizeDirectCreateLaunch(
      severalNow,
      { saveToLibrary: false, staffMode: false },
      NOW,
    )
    expect(several).toEqual({ executions: 2, schedules: 0, hasFutureStart: false })
    expect(resolveDesktopLaunchLabel(several)).toBe(ACTION_PLAN_DESKTOP_START_LABEL)
    expect(formatActionPlanSubmissionNotice(several)).toBe('Cette validation créera 2 exécutions.')

    expect(
      summarizeDirectCreateLaunch(severalNow, { saveToLibrary: true, staffMode: false }, NOW),
    ).toEqual({ executions: 0, schedules: 0, hasFutureStart: false })
  })
})
