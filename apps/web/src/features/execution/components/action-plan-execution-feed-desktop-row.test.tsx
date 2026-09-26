// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { ActionPlanExecutionFeedItem } from '@/features/action-plans/types'

import { ActionPlanExecutionFeedDesktopRow } from './action-plan-execution-feed-desktop-row'

vi.mock('../lib/use-feed-card-now', () => ({
  useFeedCardNow: () => Date.parse('2026-07-10T12:00:00Z'),
}))

afterEach(() => {
  cleanup()
})

function buildOtherPole(id: string, name: string) {
  return {
    business_unit: {
      id,
      specific_name: name,
      instance_description: '',
      active: true,
      generic: {
        key: id,
        label: name,
        description: '',
        unit_type: 'dedicated' as const,
      },
    },
    contribution_status: 'in_progress',
  }
}

function buildFeedItem(
  overrides: Partial<ActionPlanExecutionFeedItem> = {},
): ActionPlanExecutionFeedItem {
  return {
    id: 'exec-1',
    title: 'Réorganiser le stock',
    description_short: 'Desc',
    status: 'in_progress',
    requires_validation: false,
    validated_at: null,
    validated_by_display_name: null,
    pilot_business_unit: {
      id: 'bu-1',
      specific_name: 'Restauration',
      instance_description: '',
      active: true,
      generic: {
        key: 'restaurant',
        label: 'Restaurant',
        description: '',
        unit_type: 'dedicated',
      },
    },
    involved_poles: [],
    signal_summary: null,
    assignees: [{ membership_id: 'm1', display_name: 'Alice Martin' }],
    start_at: '2026-07-10T08:00:00Z',
    end_at: '2026-07-10T16:00:00Z',
    all_day: false,
    visible_from: '2026-07-09T08:00:00Z',
    is_overdue: false,
    task_count: 0,
    treated_task_count: 0,
    task_executions: [],
    last_activity_at: '2026-07-06T10:00:00Z',
    created_at: '2026-07-01T10:00:00Z',
    created_by_display_name: 'Antoine Martin',
    marked_done_at: null,
    marked_done_by_display_name: null,
    canceled_at: null,
    active_review: null,
    is_pinned: false,
    permission_hints: {
      can_mark_done: true,
      can_validate: false,
      can_reopen: false,
      can_cancel: false,
      can_update: false,
      is_pilot_pole_assignee: true,
      can_pin: true,
    },
    ...overrides,
  }
}

describe('ActionPlanExecutionFeedDesktopRow', () => {
  it('shows singular and plural other-poles badges after the pilot pole', () => {
    const { rerender } = render(
      <ActionPlanExecutionFeedDesktopRow
        item={buildFeedItem({
          involved_poles: [buildOtherPole('bu-2', 'Hôtel')],
        })}
        onSelect={vi.fn()}
      />,
    )
    expect(screen.getByText('+1 pôle')).toBeTruthy()

    rerender(
      <ActionPlanExecutionFeedDesktopRow
        item={buildFeedItem({
          involved_poles: [
            buildOtherPole('bu-2', 'Hôtel'),
            buildOtherPole('bu-3', 'Spa'),
          ],
        })}
        onSelect={vi.fn()}
      />,
    )
    expect(screen.getByText('+2 pôles')).toBeTruthy()
  })

  it('renders Validé meta, stars for active_review including 0/5, and omits Créé le', () => {
    render(
      <ActionPlanExecutionFeedDesktopRow
        item={buildFeedItem({
          status: 'done',
          validated_at: '2026-07-09T10:00:00Z',
          validated_by_display_name: 'Alice Martin',
          active_review: { stars: 0, comment: '' },
        })}
        onSelect={vi.fn()}
      />,
    )
    expect(screen.getByText('Validé')).toBeTruthy()
    expect(screen.getByText(/Validé le /)).toBeTruthy()
    expect(screen.getByRole('img', { name: 'Note : 0 sur 5' })).toBeTruthy()
    expect(screen.queryByText(/Créé le/)).toBeNull()
  })

  it('shows Annulé le when canceled_at is reliable and hides invented dates', () => {
    const { rerender } = render(
      <ActionPlanExecutionFeedDesktopRow
        item={buildFeedItem({
          status: 'canceled',
          canceled_at: '2026-07-08T10:00:00Z',
        })}
        onSelect={vi.fn()}
      />,
    )
    expect(screen.getByText(/Annulé le /)).toBeTruthy()
    expect(screen.queryByText(/Créé le/)).toBeNull()

    rerender(
      <ActionPlanExecutionFeedDesktopRow
        item={buildFeedItem({ status: 'canceled', canceled_at: null })}
        onSelect={vi.fn()}
      />,
    )
    expect(screen.queryByText(/Annulé le /)).toBeNull()
  })

  it('uses À valider and shows marked-done line when present', () => {
    render(
      <ActionPlanExecutionFeedDesktopRow
        item={buildFeedItem({
          status: 'pending_validation',
          marked_done_at: '2026-07-09T09:00:00Z',
          marked_done_by_display_name: 'Céline Dupont',
        })}
        onSelect={vi.fn()}
      />,
    )
    expect(screen.getByText('À valider')).toBeTruthy()
    expect(screen.queryByText('En attente de validation')).toBeNull()
    expect(screen.getByText(/Marqué comme terminé le /)).toBeTruthy()
    expect(screen.getByText(/Créé le /)).toBeTruthy()
  })

  it('shows Retard chip instead of RETARD text', () => {
    render(
      <ActionPlanExecutionFeedDesktopRow
        item={buildFeedItem({
          is_overdue: true,
          end_at: '2026-07-10T11:00:00Z',
        })}
        onSelect={vi.fn()}
      />,
    )
    expect(screen.getByText(/^Retard /)).toBeTruthy()
    expect(screen.queryByText(/^RETARD /)).toBeNull()
  })

  it('places Début and Fin under status badges and keeps assignees for scheduled', () => {
    render(
      <ActionPlanExecutionFeedDesktopRow
        item={buildFeedItem({
          status: 'scheduled',
          start_at: '2026-07-13T08:00:00Z',
          end_at: '2026-07-13T16:00:00Z',
        })}
        onSelect={vi.fn()}
      />,
    )
    expect(screen.getByText('Planifié')).toBeTruthy()
    expect(screen.getByText('Début')).toBeTruthy()
    expect(screen.getByText('Fin')).toBeTruthy()
    expect(screen.queryByText(/Échéance/)).toBeNull()
    expect(screen.getByText('Alice Martin')).toBeTruthy()
    const start = screen.getByText('Début')
    const end = screen.getByText('Fin')
    expect(start.parentElement?.parentElement).toBe(end.parentElement?.parentElement)
    expect(start.parentElement?.parentElement?.className).toContain('gap-x-3')
    expect(start.parentElement?.parentElement?.className).not.toContain('justify-between')
  })

  it('replaces Échéance with Début and Fin for in-progress rows', () => {
    render(<ActionPlanExecutionFeedDesktopRow item={buildFeedItem()} onSelect={vi.fn()} />)
    expect(screen.getByText('Début')).toBeTruthy()
    expect(screen.getByText('Fin')).toBeTruthy()
    expect(screen.queryByText(/Échéance/)).toBeNull()
    const row = screen.getByText('Début').parentElement?.parentElement
    expect(row?.className).toContain('flex-wrap')
    expect(row?.className).not.toContain('justify-between')
  })

  it('pins directly when can_pin and onTogglePin are provided', () => {
    const onTogglePin = vi.fn()
    const onSelect = vi.fn()
    render(
      <ActionPlanExecutionFeedDesktopRow
        item={buildFeedItem()}
        onSelect={onSelect}
        onTogglePin={onTogglePin}
      />,
    )
    fireEvent.click(screen.getByRole('button', { name: 'Épingler' }))
    expect(onTogglePin).toHaveBeenCalled()
    expect(onSelect).not.toHaveBeenCalled()
    expect(screen.queryByRole('button', { name: 'Actions du plan d’action' })).toBeNull()
  })

  it('hides pin when can_pin is false even if onTogglePin is provided', () => {
    render(
      <ActionPlanExecutionFeedDesktopRow
        item={buildFeedItem({
          permission_hints: {
            can_mark_done: true,
            can_validate: false,
            can_reopen: false,
            can_cancel: false,
            can_update: false,
            is_pilot_pole_assignee: true,
            can_pin: false,
          },
        })}
        onSelect={vi.fn()}
        onTogglePin={vi.fn()}
      />,
    )
    expect(screen.queryByRole('button', { name: 'Épingler' })).toBeNull()
  })

  it('keeps the delay chip on the created line, right-aligned', () => {
    render(
      <ActionPlanExecutionFeedDesktopRow
        item={buildFeedItem({
          is_overdue: true,
          end_at: '2026-07-10T11:00:00Z',
        })}
        onSelect={vi.fn()}
      />,
    )
    const created = screen.getByText(/Créé le/)
    const delay = screen.getByText(/^Retard /)
    expect(created.compareDocumentPosition(delay) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(created.parentElement?.parentElement?.contains(delay)).toBe(true)
  })
})
