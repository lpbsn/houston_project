// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

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
    renderForm(createActionPlanEventPlanningDraft(), {
      ...baseConfig,
      planningPersisted: false,
    })
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

  it('hides time pickers when the draft is all-day', () => {
    renderForm({
      ...createActionPlanEventPlanningDraft(),
      startDate: '2026-09-08',
      endDate: '2026-09-08',
      startTime: '',
      endTime: '',
    })
    expect(screen.getByRole('switch', { name: 'Journée entière' }).getAttribute('aria-checked')).toBe(
      'true',
    )
    expect(screen.queryByLabelText('Début — heure')).toBeNull()
    expect(screen.queryByLabelText('Fin — heure')).toBeNull()
  })
})
