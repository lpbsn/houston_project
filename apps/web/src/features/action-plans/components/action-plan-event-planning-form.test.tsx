// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ActionPlanEventPlanningForm } from './action-plan-event-planning-form'
import { createActionPlanAssigneeDraft } from '../lib/action-plan-form-validation'
import {
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

describe('ActionPlanEventPlanningForm', () => {
  afterEach(() => {
    cleanup()
  })

  it('renders core planning rows', () => {
    renderForm()
    expect(screen.getByText('Assignés')).toBeTruthy()
    expect(screen.getByText('Toute la journée')).toBeTruthy()
    expect(screen.getByText('Début')).toBeTruthy()
    expect(screen.getByText('Fin')).toBeTruthy()
    expect(screen.getByText('Répéter')).toBeTruthy()
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
    const onDraftChange = vi.fn()
    renderForm(createActionPlanEventPlanningDraft(), baseConfig, onDraftChange)
    fireEvent.click(screen.getByRole('switch', { name: 'Répéter' }))
    expect(onDraftChange).toHaveBeenCalledWith(
      expect.objectContaining({ repeatEnabled: true }),
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

  it('hides start/end time pills when all day is enabled', () => {
    renderForm({
      ...createActionPlanEventPlanningDraft(),
      allDay: true,
      startDate: '2026-07-04',
      endDate: '2026-07-04',
    })
    expect(screen.queryByLabelText('Début — heure')).toBeNull()
    expect(screen.queryByLabelText('Fin — heure')).toBeNull()
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

  it('surfaces repeat time errors on Début and Fin rows', () => {
    render(
      createElement(ActionPlanEventPlanningForm, {
        draft: { ...createActionPlanEventPlanningDraft(), repeatEnabled: true, allDay: false },
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

  it('shows per-assignee time pills even when all day is enabled', () => {
    const assignee = createActionPlanAssigneeDraft({
      membershipId: 'm1',
      businessUnitId: 'bu1',
      displayName: 'Bob',
      startAt: '2026-07-04T09:00:00.000Z',
      endAt: '2026-07-04T10:00:00.000Z',
    })
    renderForm(
      {
        ...createActionPlanEventPlanningDraft(),
        allDay: true,
        usePerAssigneeChronology: true,
        assignees: [assignee],
      },
      baseConfig,
    )
    fireEvent.click(screen.getByRole('switch', { name: 'Chronologie par assigné' }))
    expect(screen.getAllByLabelText('Début — heure').length).toBeGreaterThan(0)
    expect(screen.getAllByLabelText('Fin — heure').length).toBeGreaterThan(0)
  })

  it('shows chronologie par assigné toggle under assignés without advanced section', () => {
    renderForm()
    expect(screen.getByRole('switch', { name: 'Chronologie par assigné' })).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Chronologie avancée' })).toBeNull()
  })
})
