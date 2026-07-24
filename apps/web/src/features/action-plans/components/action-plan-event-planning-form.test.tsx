// @vitest-environment jsdom

import { createElement, useState } from 'react'
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ActionPlanEventPlanningForm } from './action-plan-event-planning-form'
import { createActionPlanAssigneeDraft } from '../lib/action-plan-form-validation'
import {
  combineDateAndTimeToIso,
  createActionPlanEventPlanningDraft,
  type ActionPlanEventPlanningConfig,
  type ActionPlanEventPlanningDraft,
} from '../lib/action-plan-event-planning-form'

vi.mock('./action-plan-assignees-sheet', () => ({
  ActionPlanAssigneesSheet: () => null,
}))

const baseConfig: ActionPlanEventPlanningConfig = {
  canEditAssignees: true,
  canSchedule: true,
  staffMode: false,
  showAdvancedChronology: true,
  hideAssignees: false,
}

type DraftUpdate =
  | ActionPlanEventPlanningDraft
  | ((previous: ActionPlanEventPlanningDraft) => ActionPlanEventPlanningDraft)

function resolveDraftUpdate(
  update: DraftUpdate,
  previous: ActionPlanEventPlanningDraft,
): ActionPlanEventPlanningDraft {
  return typeof update === 'function' ? update(previous) : update
}

function renderForm(
  draft: ActionPlanEventPlanningDraft = createActionPlanEventPlanningDraft(),
  config = baseConfig,
  onDraftChange = vi.fn(),
) {
  return render(
    createElement(ActionPlanEventPlanningForm, {
      draft,
      config,
      establishmentId: 'est-1',
      pilotBusinessUnitId: 'bu-1',
      onDraftChange,
    }),
  )
}

function StatefulPlanningHarness({
  initialDraft,
  config = baseConfig,
}: {
  initialDraft: ActionPlanEventPlanningDraft
  config?: ActionPlanEventPlanningConfig
}) {
  const [draft, setDraft] = useState(initialDraft)
  return createElement(
    'div',
    null,
    createElement('pre', { 'data-testid': 'planning-draft-snapshot' }, JSON.stringify({
      startDate: draft.startDate,
      startTime: draft.startTime,
      endDate: draft.endDate,
      endTime: draft.endTime,
      repeatEnabled: draft.repeatEnabled,
    })),
    createElement(ActionPlanEventPlanningForm, {
      draft,
      config,
      establishmentId: 'est-1',
      pilotBusinessUnitId: 'bu-1',
      onDraftChange: setDraft,
    }),
  )
}

describe('ActionPlanEventPlanningForm', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    cleanup()
    vi.useRealTimers()
  })

  it('renders core global planning rows', () => {
    renderForm()
    expect(screen.getByText('Assignés')).toBeTruthy()
    expect(screen.getByText('Chronologie commune')).toBeTruthy()
    expect(screen.getByText('Début')).toBeTruthy()
    expect(screen.getByText('Fin')).toBeTruthy()
    expect(screen.getByText('Répéter')).toBeTruthy()
    expect(screen.queryByText('Toute la journée')).toBeNull()
  })

  it('shows staff assignee summary as read-only', () => {
    renderForm(createActionPlanEventPlanningDraft(), {
      ...baseConfig,
      canEditAssignees: false,
      staffMode: true,
      showAdvancedChronology: false,
      staffDisplayName: 'Alice',
    })
    expect(screen.getByText('Alice')).toBeTruthy()
  })

  it('toggles repeat fields with a switch', () => {
    const initial = createActionPlanEventPlanningDraft()
    const onDraftChange = vi.fn()
    renderForm(initial, baseConfig, onDraftChange)
    fireEvent.click(screen.getByRole('switch', { name: 'Répéter' }))
    expect(resolveDraftUpdate(onDraftChange.mock.calls[0][0], initial)).toEqual(
      expect.objectContaining({ repeatEnabled: true }),
    )
  })

  it('preserves a distinct one-shot end date when repeat is enabled', () => {
    const initial = {
      ...createActionPlanEventPlanningDraft(),
      startDate: '2026-07-04',
      endDate: '2026-07-08',
    }
    const onDraftChange = vi.fn()
    renderForm(initial, baseConfig, onDraftChange)

    fireEvent.click(screen.getByRole('switch', { name: 'Répéter' }))

    expect(resolveDraftUpdate(onDraftChange.mock.calls[0][0], initial)).toEqual(
      expect.objectContaining({ repeatEnabled: true, endDate: '2026-07-08' }),
    )
  })

  it('preserves end date when repeat is toggled off again', () => {
    const initial = {
      ...createActionPlanEventPlanningDraft(),
      startDate: '2026-07-04',
      endDate: '2026-07-08',
      repeatEnabled: true,
    }
    const onDraftChange = vi.fn()
    renderForm(initial, baseConfig, onDraftChange)

    fireEvent.click(screen.getByRole('switch', { name: 'Répéter' }))

    expect(resolveDraftUpdate(onDraftChange.mock.calls[0][0], initial)).toEqual(
      expect.objectContaining({ repeatEnabled: false, endDate: '2026-07-08' }),
    )
  })

  it('hides repeat toggle when scheduling is not allowed', () => {
    renderForm(createActionPlanEventPlanningDraft(), {
      ...baseConfig,
      canSchedule: false,
    })
    expect(screen.queryByText('Répéter')).toBeNull()
  })

  it('hides assignees when configured', () => {
    renderForm(createActionPlanEventPlanningDraft(), {
      ...baseConfig,
      hideAssignees: true,
    })
    expect(screen.queryByText('Assignés')).toBeNull()
  })

  it('always shows start and end time pills in global mode', () => {
    renderForm({
      ...createActionPlanEventPlanningDraft(),
      startDate: '2026-07-04',
      endDate: '2026-07-04',
    })
    expect(screen.getByLabelText('Début — heure')).toBeTruthy()
    expect(screen.getByLabelText('Fin — heure')).toBeTruthy()
    expect(screen.getByLabelText('Début — date')).toBeTruthy()
    expect(screen.getByLabelText('Fin — date')).toBeTruthy()
  })

  it('opens and closes the shared start date picker', () => {
    renderForm({
      ...createActionPlanEventPlanningDraft(),
      startDate: '2026-07-04',
    })
    const datePill = screen.getByLabelText('Début — date')
    fireEvent.click(datePill)
    expect(screen.getByRole('button', { name: '4 juillet 2026' })).toBeTruthy()
    fireEvent.click(datePill)
    expect(screen.queryByRole('button', { name: '4 juillet 2026' })).toBeNull()
  })

  it('closes an open picker when another pill is tapped', () => {
    renderForm({
      ...createActionPlanEventPlanningDraft(),
      startDate: '2026-07-04',
      endDate: '2026-07-05',
    })
    fireEvent.click(screen.getByLabelText('Début — date'))
    expect(screen.getByLabelText('Début — date').getAttribute('aria-pressed')).toBe('true')
    fireEvent.click(screen.getByLabelText('Fin — date'))
    expect(screen.getByLabelText('Début — date').getAttribute('aria-pressed')).toBe('false')
    expect(screen.getByLabelText('Fin — date').getAttribute('aria-pressed')).toBe('true')
    expect(screen.getByRole('button', { name: '5 juillet 2026' })).toBeTruthy()
  })

  it('surfaces repeat time errors on execution slot rows', () => {
    render(
      createElement(ActionPlanEventPlanningForm, {
        draft: { ...createActionPlanEventPlanningDraft(), repeatEnabled: true },
        config: baseConfig,
        establishmentId: 'est-1',
        pilotBusinessUnitId: 'bu-1',
        fieldErrors: {
          startTime: "L'heure de début est requise.",
          endTime: "L'heure de fin est requise.",
        },
        onDraftChange: vi.fn(),
      }),
    )
    expect(screen.getByText("L'heure de début est requise.")).toBeTruthy()
    expect(screen.getByText("L'heure de fin est requise.")).toBeTruthy()
  })

  it('shows chronologie par assigné toggle under assignés without advanced section', () => {
    renderForm()
    expect(screen.getByRole('switch', { name: 'Chronologie par assigné' })).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Chronologie avancée' })).toBeNull()
  })

  it('hides global planning when per-assignee chronology is enabled', () => {
    const assignee = createActionPlanAssigneeDraft({
      membershipId: 'm1',
      businessUnitId: 'bu1',
      displayName: 'Bob',
    })
    renderForm({
      ...createActionPlanEventPlanningDraft(),
      usePerAssigneeChronology: true,
      assignees: [assignee],
    })
    expect(screen.getAllByText('Chronologie par assigné').length).toBeGreaterThan(0)
    expect(screen.getAllByLabelText('Début — date')).toHaveLength(1)
    expect(screen.getAllByLabelText('Fin — date')).toHaveLength(1)
    expect(screen.getAllByRole('switch', { name: 'Répéter' })).toHaveLength(1)
    expect(screen.getAllByText('Bob').length).toBeGreaterThan(0)
  })

  it('shows date pills on assignee card when repeat is off', () => {
    const assignee = createActionPlanAssigneeDraft({
      membershipId: 'm1',
      businessUnitId: 'bu1',
      displayName: 'Bob',
      startAt: combineDateAndTimeToIso('2026-07-04', '09:00', 'start'),
      endAt: combineDateAndTimeToIso('2026-07-05', '10:00', 'end'),
    })
    renderForm({
      ...createActionPlanEventPlanningDraft(),
      usePerAssigneeChronology: true,
      assignees: [assignee],
    })
    expect(screen.getByLabelText('Début — date')).toBeTruthy()
    expect(screen.getByLabelText('Fin — date')).toBeTruthy()
    expect(screen.getByLabelText('Début — heure')).toBeTruthy()
    expect(screen.getByLabelText('Fin — heure')).toBeTruthy()
  })

  it('shows recurrence fields in global mode when repeat is enabled', () => {
    renderForm({
      ...createActionPlanEventPlanningDraft(),
      repeatEnabled: true,
      startDate: '2026-07-04',
      startTime: '09:00',
      endTime: '10:00',
    })
    expect(screen.getByText('Début de la récurrence')).toBeTruthy()
    expect(screen.getByText('Fin de la récurrence')).toBeTruthy()
    expect(screen.getByText("Début du créneau d'exécution")).toBeTruthy()
    expect(screen.getByText("Fin du créneau d'exécution")).toBeTruthy()
    expect(screen.queryByLabelText('Début de la récurrence — heure')).toBeNull()
    expect(screen.getByLabelText('Début de la récurrence — date')).toBeTruthy()
    expect(screen.getByLabelText("Début du créneau d'exécution — heure")).toBeTruthy()
    expect(screen.getByLabelText("Fin du créneau d'exécution — heure")).toBeTruthy()
    expect(screen.queryByLabelText('Début — date')).toBeNull()
    expect(screen.queryByLabelText('Fin — date')).toBeNull()
    expect(screen.getByText('Jours')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Lundi' })).toBeTruthy()
  })

  it('shows recurrence fields on assignee card when repeat is enabled', () => {
    const assignee = createActionPlanAssigneeDraft({
      membershipId: 'm1',
      businessUnitId: 'bu1',
      displayName: 'Bob',
      repeatEnabled: true,
      startAt: combineDateAndTimeToIso('2026-07-04', '09:00', 'start'),
      endAt: combineDateAndTimeToIso('2026-07-04', '10:00', 'end'),
    })
    renderForm({
      ...createActionPlanEventPlanningDraft(),
      usePerAssigneeChronology: true,
      assignees: [assignee],
    })
    expect(screen.getByText('Début de la récurrence')).toBeTruthy()
    expect(screen.getByText('Fin de la récurrence')).toBeTruthy()
    expect(screen.getByText("Début du créneau d'exécution")).toBeTruthy()
    expect(screen.getByText("Fin du créneau d'exécution")).toBeTruthy()
    expect(screen.queryByLabelText('Début de la récurrence — heure')).toBeNull()
    expect(screen.getByLabelText('Début de la récurrence — date')).toBeTruthy()
    expect(screen.getByText('Jours')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Lundi' })).toBeTruthy()
  })

  it('disables assignee action button while pending', () => {
    const assignee = createActionPlanAssigneeDraft({
      membershipId: 'm1',
      businessUnitId: 'bu1',
      displayName: 'Bob',
      startAt: combineDateAndTimeToIso('2026-07-04', '09:00', 'start'),
      endAt: combineDateAndTimeToIso('2026-07-05', '10:00', 'end'),
    })
    renderForm(
      {
        ...createActionPlanEventPlanningDraft(),
        usePerAssigneeChronology: true,
        assignees: [assignee],
      },
      {
        ...baseConfig,
        assigneeActionPending: { [assignee.id]: 'launch' },
      },
    )

    expect(screen.getByRole('button', { name: 'Lancer pour cet assigné' })).toHaveProperty(
      'disabled',
      true,
    )
  })

  it('shows planning not persisted hint when configured', () => {
    render(
      createElement(ActionPlanEventPlanningForm, {
        draft: createActionPlanEventPlanningDraft(),
        config: { ...baseConfig, planningPersisted: false },
        establishmentId: 'est-1',
        pilotBusinessUnitId: 'bu-1',
        onDraftChange: vi.fn(),
      }),
    )
    expect(
      screen.getByText("La planification n'est pas enregistrée avec le template."),
    ).toBeTruthy()
  })

  it('hides Maintenant when planning is not persisted', () => {
    renderForm(createActionPlanEventPlanningDraft(), {
      ...baseConfig,
      planningPersisted: false,
    })
    expect(screen.queryByRole('button', { name: 'Maintenant' })).toBeNull()
  })

  it('fills shared start from Maintenant without changing end', () => {
    vi.setSystemTime(new Date(2026, 6, 19, 10, 2, 0))
    const initial = {
      ...createActionPlanEventPlanningDraft(),
      startDate: '2026-07-01',
      startTime: '09:00',
      endDate: '2026-07-02',
      endTime: '18:00',
    }
    const onDraftChange = vi.fn()
    renderForm(initial, baseConfig, onDraftChange)

    fireEvent.click(screen.getByRole('button', { name: 'Maintenant' }))

    expect(resolveDraftUpdate(onDraftChange.mock.calls[0][0], initial)).toEqual(
      expect.objectContaining({
        startDate: '2026-07-19',
        startTime: '10:00',
        endDate: '2026-07-02',
        endTime: '18:00',
      }),
    )
  })

  it('updates only the targeted assignee start with Maintenant', () => {
    vi.setSystemTime(new Date(2026, 6, 19, 10, 2, 0))
    const onDraftChange = vi.fn()
    const first = createActionPlanAssigneeDraft({
      membershipId: 'm1',
      businessUnitId: 'bu1',
      displayName: 'Alice',
      startAt: combineDateAndTimeToIso('2026-07-01', '09:00', 'start'),
      endAt: combineDateAndTimeToIso('2026-07-01', '10:00', 'end'),
    })
    const second = createActionPlanAssigneeDraft({
      membershipId: 'm2',
      businessUnitId: 'bu1',
      displayName: 'Bob',
      startAt: combineDateAndTimeToIso('2026-07-02', '11:00', 'start'),
      endAt: combineDateAndTimeToIso('2026-07-02', '12:00', 'end'),
    })
    const initial = {
      ...createActionPlanEventPlanningDraft(),
      usePerAssigneeChronology: true,
      assignees: [first, second],
    }
    renderForm(initial, baseConfig, onDraftChange)

    const nowButtons = screen.getAllByRole('button', { name: 'Maintenant' })
    expect(nowButtons).toHaveLength(2)
    fireEvent.click(nowButtons[0])

    expect(onDraftChange).toHaveBeenCalledTimes(1)
    const nextDraft = resolveDraftUpdate(onDraftChange.mock.calls[0][0], initial)
    expect(nextDraft.assignees[0].startAt).toBe(
      combineDateAndTimeToIso('2026-07-19', '10:00', 'start'),
    )
    expect(nextDraft.assignees[0].endAt).toBe(first.endAt)
    expect(nextDraft.assignees[1]).toEqual(second)
  })

  it('keeps both patches from the same render before any intermediate rerender', () => {
    vi.setSystemTime(new Date(2026, 6, 19, 10, 2, 0))
    const initial = {
      ...createActionPlanEventPlanningDraft(),
      startDate: '2026-07-01',
      startTime: '09:00',
      endDate: '2026-07-02',
      endTime: '18:00',
      repeatEnabled: false,
    }

    render(createElement(StatefulPlanningHarness, { initialDraft: initial }))

    act(() => {
      fireEvent.click(screen.getByRole('button', { name: 'Maintenant' }))
      fireEvent.click(screen.getByRole('switch', { name: 'Répéter' }))
    })

    const snapshot = JSON.parse(
      screen.getByTestId('planning-draft-snapshot').textContent ?? '{}',
    ) as {
      startDate: string
      startTime: string
      endDate: string
      endTime: string
      repeatEnabled: boolean
    }

    expect(snapshot).toEqual({
      startDate: '2026-07-19',
      startTime: '10:00',
      endDate: '2026-07-02',
      endTime: '18:00',
      repeatEnabled: true,
    })
  })
})
