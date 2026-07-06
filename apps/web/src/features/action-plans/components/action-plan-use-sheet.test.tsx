// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ActionPlanUseSheet } from './action-plan-use-sheet'
import type { ActionPlanEventPlanningDraft } from '../lib/action-plan-event-planning-form'

vi.mock('./action-plan-event-planning-form', async (importOriginal) => {
  const actual = await importOriginal<typeof import('./action-plan-event-planning-form')>()
  return {
    ...actual,
    ActionPlanEventPlanningForm: ({
      draft,
      onDraftChange,
    }: {
      draft: ActionPlanEventPlanningDraft
      onDraftChange: (next: ActionPlanEventPlanningDraft) => void
    }) => (
      <div>
        <button
          type="button"
          onClick={() => onDraftChange({ ...draft, repeatEnabled: true, recurrenceDays: ['monday'] })}
        >
          Activer repeat
        </button>
        <button
          type="button"
          onClick={() =>
            onDraftChange({
              ...draft,
              repeatEnabled: true,
              recurrenceDays: ['monday'],
              recurrenceEndDate: '2026-12-31',
              startDate: '2026-07-01',
              startTime: '09:00',
              endTime: '10:00',
            })
          }
        >
          Compléter repeat
        </button>
      </div>
    ),
  }
})

const defaultProps = {
  establishmentId: 'est-1',
  pilotBusinessUnitId: 'bu-1',
  isPending: false,
  canSchedule: true,
  onClose: vi.fn(),
  onConfirm: vi.fn(),
  onScheduleConfirm: vi.fn(),
}

describe('ActionPlanUseSheet', () => {
  afterEach(() => {
    cleanup()
  })

  it('resets local state when closed and reopened', () => {
    const { rerender } = render(
      createElement(ActionPlanUseSheet, {
        ...defaultProps,
        open: true,
      }),
    )

    fireEvent.click(screen.getByRole('button', { name: 'Activer repeat' }))
    expect(screen.getByRole('button', { name: 'Planifier la récurrence' })).toBeTruthy()

    rerender(
      createElement(ActionPlanUseSheet, {
        ...defaultProps,
        open: false,
      }),
    )

    rerender(
      createElement(ActionPlanUseSheet, {
        ...defaultProps,
        open: true,
      }),
    )

    expect(screen.getByRole('button', { name: "Lancer l'exécution" })).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Planifier la récurrence' })).toBeNull()
  })

  it('calls onConfirm for one-shot launch', () => {
    const onConfirm = vi.fn()
    const onScheduleConfirm = vi.fn()

    render(
      createElement(ActionPlanUseSheet, {
        open: true,
        establishmentId: 'est-1',
        pilotBusinessUnitId: 'bu-1',
        isPending: false,
        canSchedule: true,
        onClose: vi.fn(),
        onConfirm,
        onScheduleConfirm,
      }),
    )

    fireEvent.click(screen.getByRole('button', { name: "Lancer l'exécution" }))
    expect(onConfirm).toHaveBeenCalled()
    expect(onScheduleConfirm).not.toHaveBeenCalled()
  })

  it('calls onScheduleConfirm when repeat is configured', () => {
    const onConfirm = vi.fn()
    const onScheduleConfirm = vi.fn()

    render(
      createElement(ActionPlanUseSheet, {
        open: true,
        establishmentId: 'est-1',
        pilotBusinessUnitId: 'bu-1',
        isPending: false,
        canSchedule: true,
        onClose: vi.fn(),
        onConfirm,
        onScheduleConfirm,
      }),
    )

    fireEvent.click(screen.getByRole('button', { name: 'Activer repeat' }))
    fireEvent.click(screen.getByRole('button', { name: 'Compléter repeat' }))
    fireEvent.click(screen.getByRole('button', { name: 'Planifier la récurrence' }))

    expect(onScheduleConfirm).toHaveBeenCalledWith(
      expect.objectContaining({
        recurrence_days: ['monday'],
        use_shared_chronology: true,
      }),
    )
    expect(onConfirm).not.toHaveBeenCalled()
  })
})
