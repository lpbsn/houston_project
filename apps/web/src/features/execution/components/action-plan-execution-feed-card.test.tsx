// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { ActionPlanExecutionFeedItem } from '@/features/action-plans/types'

import { ActionPlanExecutionFeedCard } from './action-plan-execution-feed-card'

vi.mock('../lib/use-feed-card-now', () => ({
  useFeedCardNow: () => Date.parse('2026-07-10T12:00:00Z'),
}))

afterEach(() => {
  cleanup()
})

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
    involved_poles: [
      {
        business_unit: {
          id: 'bu-2',
          specific_name: 'Hôtel',
          instance_description: '',
          active: true,
          generic: {
            key: 'hotel',
            label: 'Hôtel',
            description: '',
            unit_type: 'dedicated',
          },
        },
        contribution_status: 'in_progress',
      },
    ],
    signal_summary: null,
    assignees: [
      { membership_id: 'm1', display_name: 'Leonard Boisson' },
      { membership_id: 'm2', display_name: 'Céline Dupont' },
      { membership_id: 'm3', display_name: 'Alice Martin' },
    ],
    start_at: '2026-07-10T08:00:00Z',
    end_at: '2026-07-10T16:00:00Z',
    all_day: false,
    visible_from: '2026-07-09T08:00:00Z',
    is_overdue: false,
    task_count: 3,
    treated_task_count: 1,
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

describe('ActionPlanExecutionFeedCard', () => {
  it('renders in-progress anatomy without task progress', () => {
    render(<ActionPlanExecutionFeedCard item={buildFeedItem()} onSelect={vi.fn()} />)
    expect(screen.getByText('En cours')).toBeTruthy()
    expect(screen.getByText('Réorganiser le stock')).toBeTruthy()
    expect(screen.getByText('Créé par Antoine Martin')).toBeTruthy()
    expect(screen.getByText(/Leonard, Céline \+1|Leonard Boisson/)).toBeTruthy()
    expect(screen.queryByText(/Tâche/)).toBeNull()
    expect(screen.getByRole('progressbar', { name: 'Progression temporelle' })).toBeTruthy()
  })

  it('shows Non assigné when empty', () => {
    render(
      <ActionPlanExecutionFeedCard
        item={buildFeedItem({ assignees: [] })}
        onSelect={vi.fn()}
      />,
    )
    expect(screen.getByText('Non assigné')).toBeTruthy()
  })

  it('shows overdue label when is_overdue', () => {
    render(
      <ActionPlanExecutionFeedCard
        item={buildFeedItem({ is_overdue: true, end_at: '2026-07-10T11:00:00Z' })}
        onSelect={vi.fn()}
      />,
    )
    expect(screen.getByText(/Retard/)).toBeTruthy()
  })

  it('calls onTogglePin without opening the card', () => {
    const onSelect = vi.fn()
    const onTogglePin = vi.fn()
    render(
      <ActionPlanExecutionFeedCard
        item={buildFeedItem()}
        onSelect={onSelect}
        onTogglePin={onTogglePin}
      />,
    )
    fireEvent.click(screen.getByRole('button', { name: 'Épingler' }))
    expect(onTogglePin).toHaveBeenCalled()
    expect(onSelect).not.toBeCalled()
  })

  it('hides pin when can_pin is false', () => {
    render(
      <ActionPlanExecutionFeedCard
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

  it('renders pending validation without temporal bar', () => {
    render(
      <ActionPlanExecutionFeedCard
        item={buildFeedItem({ status: 'pending_validation' })}
        onSelect={vi.fn()}
      />,
    )
    expect(screen.getByText('À valider')).toBeTruthy()
    expect(screen.queryByRole('progressbar')).toBeNull()
  })

  it('keeps À valider soft tone and restores status badge colors', () => {
    const { rerender } = render(
      <ActionPlanExecutionFeedCard
        item={buildFeedItem({ status: 'in_progress' })}
        onSelect={vi.fn()}
      />,
    )
    expect(screen.getByText('En cours').className).toContain('bg-[#3A7A96]')

    rerender(
      <ActionPlanExecutionFeedCard
        item={buildFeedItem({
          status: 'done',
          validated_at: '2026-07-09T10:00:00Z',
          validated_by_display_name: 'Alice',
        })}
        onSelect={vi.fn()}
      />,
    )
    expect(screen.getByText('Validé').className).toContain('bg-[#1D9E75]')

    rerender(
      <ActionPlanExecutionFeedCard
        item={buildFeedItem({ status: 'scheduled' })}
        onSelect={vi.fn()}
      />,
    )
    expect(screen.getByText('Planifié').className).toContain('bg-[#8B6914]')

    rerender(
      <ActionPlanExecutionFeedCard
        item={buildFeedItem({ status: 'canceled', canceled_at: '2026-07-08T10:00:00Z' })}
        onSelect={vi.fn()}
      />,
    )
    expect(screen.getByText('Annulé').className).toContain('bg-[#E8E6DF]')

    rerender(
      <ActionPlanExecutionFeedCard
        item={buildFeedItem({ status: 'pending_validation' })}
        onSelect={vi.fn()}
      />,
    )
    const pending = screen.getByText('À valider')
    expect(pending.className).toContain('bg-[#F5E6C8]')
    expect(pending.className).toContain('text-[#8A5A12]')
    expect(pending.className).not.toContain('bg-[#EF9F27]')
  })

  it('omits terminal date when marked_done_at missing', () => {
    render(
      <ActionPlanExecutionFeedCard
        item={buildFeedItem({ status: 'done', marked_done_at: null })}
        onSelect={vi.fn()}
      />,
    )
    expect(screen.getByText('Terminé')).toBeTruthy()
    expect(screen.queryByText(/Terminé le/)).toBeNull()
  })
})
