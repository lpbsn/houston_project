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
        <button
          type="button"
          onClick={() =>
            onDraftChange({
              ...draft,
              usePerAssigneeChronology: true,
              assignees: [
                {
                  id: 'a1',
                  membershipId: 'm1',
                  businessUnitId: 'bu1',
                  displayName: 'Alice',
                  startAt: '2026-07-01T07:00:00.000Z',
                  endAt: '2026-07-01T08:00:00.000Z',
                  visibleFrom: '',
                  repeatEnabled: false,
                  recurrenceDays: [],
                  recurrenceEndDate: '',
                },
              ],
              startDate: '2026-07-01',
            })
          }
        >
          Activer per-assignee
        </button>
        <button
          type="button"
          onClick={() =>
            onDraftChange({
              ...draft,
              usePerAssigneeChronology: true,
              assignees: [
                {
                  id: 'a-recurring',
                  membershipId: 'm1',
                  businessUnitId: 'bu1',
                  displayName: 'Alice',
                  startAt: '2026-07-12T03:00:00.000Z',
                  endAt: '2026-07-12T14:05:00.000Z',
                  visibleFrom: '',
                  repeatEnabled: true,
                  recurrenceDays: ['tuesday', 'thursday', 'saturday'],
                  recurrenceEndDate: '2026-07-25',
                },
                {
                  id: 'a-one-shot',
                  membershipId: 'm2',
                  businessUnitId: 'bu1',
                  displayName: 'Bob',
                  startAt: '2026-07-11T03:00:00.000Z',
                  endAt: '2026-07-25T06:00:00.000Z',
                  visibleFrom: '',
                  repeatEnabled: false,
                  recurrenceDays: [],
                  recurrenceEndDate: '',
                },
              ],
            })
          }
        >
          Activer mixte
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
  onPlanningSubmit: vi.fn(),
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
    expect(screen.getByRole('button', { name: "Lancer l'exécution" })).toBeTruthy()

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

    const launchButton = screen.getByRole('button', { name: "Lancer l'exécution" })
    expect(launchButton).toBeTruthy()
    expect(launchButton.className).toContain('bg-[#114660]')
    expect(screen.queryByRole('button', { name: 'Planifier la récurrence' })).toBeNull()
  })

  it('calls onPlanningSubmit for one-shot launch', () => {
    const onPlanningSubmit = vi.fn()

    render(
      createElement(ActionPlanUseSheet, {
        open: true,
        establishmentId: 'est-1',
        pilotBusinessUnitId: 'bu-1',
        isPending: false,
        canSchedule: true,
        onClose: vi.fn(),
        onPlanningSubmit,
      }),
    )

    fireEvent.click(screen.getByRole('button', { name: "Lancer l'exécution" }))
    expect(onPlanningSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        kind: 'planning',
        body: expect.objectContaining({
          use_shared_chronology: true,
          items: expect.arrayContaining([
            expect.objectContaining({ kind: 'execution' }),
          ]),
        }),
      }),
    )
  })

  it('calls onPlanningSubmit for global repeat schedule', () => {
    const onPlanningSubmit = vi.fn()

    render(
      createElement(ActionPlanUseSheet, {
        open: true,
        establishmentId: 'est-1',
        pilotBusinessUnitId: 'bu-1',
        isPending: false,
        canSchedule: true,
        onClose: vi.fn(),
        onPlanningSubmit,
      }),
    )

    fireEvent.click(screen.getByRole('button', { name: 'Activer repeat' }))
    fireEvent.click(screen.getByRole('button', { name: 'Compléter repeat' }))
    fireEvent.click(screen.getByRole('button', { name: "Lancer l'exécution" }))

    expect(onPlanningSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        kind: 'planning',
        body: expect.objectContaining({
          use_shared_chronology: true,
          items: [
            expect.objectContaining({
              kind: 'schedule',
              recurrence_days: ['monday'],
            }),
          ],
        }),
      }),
    )
  })

  it('shows global launch when per-assignee chronology is active', () => {
    const onPlanningSubmit = vi.fn()

    render(
      createElement(ActionPlanUseSheet, {
        ...defaultProps,
        open: true,
        onPlanningSubmit,
      }),
    )

    fireEvent.click(screen.getByRole('button', { name: 'Activer per-assignee' }))
    fireEvent.click(screen.getByRole('button', { name: "Lancer l'exécution" }))

    expect(screen.getByRole('button', { name: "Lancer l'exécution" })).toBeTruthy()
    expect(onPlanningSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        kind: 'planning',
        body: expect.objectContaining({
          use_shared_chronology: false,
          items: [
            expect.objectContaining({
              kind: 'execution',
              primary_membership_id: 'm1',
            }),
          ],
        }),
      }),
    )
  })

  it('keeps static launch label for schedule and planning actions', () => {
    render(
      createElement(ActionPlanUseSheet, {
        ...defaultProps,
        open: true,
      }),
    )

    expect(screen.getByRole('button', { name: "Lancer l'exécution" })).toBeTruthy()
    expect(
      screen.queryByText('Une exécution ponctuelle sera lancée immédiatement.'),
    ).toBeNull()

    fireEvent.click(screen.getByRole('button', { name: 'Activer repeat' }))
    fireEvent.click(screen.getByRole('button', { name: 'Compléter repeat' }))

    expect(screen.getByRole('button', { name: "Lancer l'exécution" })).toBeTruthy()
    expect(
      screen.queryByText(
        'Une récurrence sera créée. Les prochaines exécutions apparaîtront dans le feed.',
      ),
    ).toBeNull()

    fireEvent.click(screen.getByRole('button', { name: 'Activer mixte' }))

    expect(screen.getByRole('button', { name: "Lancer l'exécution" })).toBeTruthy()
    expect(
      screen.queryByText(
        'Une récurrence sera planifiée et une exécution ponctuelle sera lancée.',
      ),
    ).toBeNull()
  })

  it('submits mixed per-assignee planning from global action', () => {
    const onPlanningSubmit = vi.fn()

    render(
      createElement(ActionPlanUseSheet, {
        ...defaultProps,
        open: true,
        onPlanningSubmit,
      }),
    )

    fireEvent.click(screen.getByRole('button', { name: 'Activer mixte' }))
    fireEvent.click(screen.getByRole('button', { name: "Lancer l'exécution" }))

    expect(onPlanningSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        kind: 'planning',
        body: expect.objectContaining({
          use_shared_chronology: false,
          items: expect.arrayContaining([
            expect.objectContaining({
              kind: 'schedule',
              primary_membership_id: 'm1',
            }),
            expect.objectContaining({
              kind: 'execution',
              primary_membership_id: 'm2',
            }),
          ]),
        }),
      }),
    )
  })
})
