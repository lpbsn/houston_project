// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { ActionPlanExecutionFeedItem } from '@/features/action-plans/types'

import { ActionPlanExecutionFeedCard } from './action-plan-execution-feed-card'

const onSelect = vi.fn()

function buildFeedItem(
  overrides: Partial<ActionPlanExecutionFeedItem> = {},
): ActionPlanExecutionFeedItem {
  return {
    id: 'execution-1',
    title: 'Plan incendie',
    description_short: 'Description longue à ne pas afficher',
    status: 'in_progress',
    requires_validation: false,
    pilot_business_unit: { id: 'bu-1', key: 'restaurant', label: 'Restaurant' },
    involved_poles: [
      {
        business_unit: { id: 'bu-2', key: 'maintenance', label: 'Maintenance' },
      },
    ],
    signal_summary: null,
    assignees: [{ membership_id: 'member-1', display_name: 'Alice Martin' }],
    end_at: '2026-07-06T18:30:00Z',
    is_overdue: false,
    task_count: 4,
    treated_task_count: 1,
    task_executions: [
      {
        position: 1,
        task: 'Tâche 1',
        status: 'done',
        business_unit: { id: 'bu-1', key: 'restaurant', label: 'Restaurant' },
      },
      {
        position: 2,
        task: 'Tâche 2',
        status: 'pending',
        business_unit: { id: 'bu-1', key: 'restaurant', label: 'Restaurant' },
      },
    ],
    last_activity_at: '2026-07-06T10:00:00Z',
    created_at: '2026-07-06T08:00:00Z',
    is_pinned: false,
    permission_hints: {
      can_mark_done: true,
      can_validate: false,
      can_reopen: false,
      can_cancel: false,
      is_pilot_pole_assignee: true,
      can_pin: true,
    },
    ...overrides,
  }
}

beforeEach(() => {
  vi.clearAllMocks()
})

afterEach(() => {
  cleanup()
})

describe('ActionPlanExecutionFeedCard', () => {
  it('shows compact pilotage meta and hides description and task previews', () => {
    render(<ActionPlanExecutionFeedCard item={buildFeedItem()} onSelect={onSelect} />)

    expect(screen.getByText('Plan incendie')).toBeTruthy()
    expect(screen.getByText('Tâche 1/4')).toBeTruthy()
    expect(screen.getByText(/Échéance :/)).toBeTruthy()

    const deadlineNode = screen.getByText(/Échéance :/)
    const taskProgressNode = screen.getByText('Tâche 1/4')
    expect(
      deadlineNode.compareDocumentPosition(taskProgressNode) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy()
    expect(screen.getByText('Restaurant')).toBeTruthy()
    expect(screen.queryByText('Pôle pilote : Restaurant')).toBeNull()
    expect(screen.getByText('Alice Martin')).toBeTruthy()
    expect(screen.getByText('En cours')).toBeTruthy()

    expect(screen.queryByText('Description longue à ne pas afficher')).toBeNull()
    expect(screen.queryByText('Tâche 1')).toBeNull()
    expect(screen.queryByText('Tâche 2')).toBeNull()
    expect(screen.queryByText(/Pôles impliqués/)).toBeNull()
  })

  it('highlights overdue deadline', () => {
    render(
      <ActionPlanExecutionFeedCard
        item={buildFeedItem({ is_overdue: true })}
        onSelect={onSelect}
      />,
    )

    const deadline = screen.getByText(/Échéance :/)
    expect(deadline.className).toContain('text-[#E24B4A]')
  })

  it('omits task progress when task_count is zero', () => {
    render(
      <ActionPlanExecutionFeedCard
        item={buildFeedItem({ task_count: 0, treated_task_count: 0 })}
        onSelect={onSelect}
      />,
    )

    expect(screen.queryByText(/Tâche \d+\/\d+/)).toBeNull()
  })

  it('shows task progress only when end_at is null', () => {
    render(
      <ActionPlanExecutionFeedCard
        item={buildFeedItem({ end_at: null })}
        onSelect={onSelect}
      />,
    )

    expect(screen.queryByText(/Échéance :/)).toBeNull()
    expect(screen.getByText('Tâche 1/4')).toBeTruthy()
  })

  it('renders distinct pending validation card without duplicate status badge', () => {
    render(
      <ActionPlanExecutionFeedCard
        item={buildFeedItem({ status: 'pending_validation' })}
        onSelect={onSelect}
      />,
    )

    expect(screen.getByText('En attente de validation')).toBeTruthy()
    expect(screen.queryByText('En cours')).toBeNull()
    expect(screen.getAllByText('En attente de validation')).toHaveLength(1)
  })

  it('navigates to detail on click', () => {
    render(<ActionPlanExecutionFeedCard item={buildFeedItem()} onSelect={onSelect} />)

    fireEvent.click(screen.getByRole('button'))

    expect(onSelect).toHaveBeenCalledWith('execution-1')
  })

  it('shows pilot pole badge on the meta row with title below', () => {
    render(
      <ActionPlanExecutionFeedCard
        item={buildFeedItem()}
        onSelect={onSelect}
        onOpenActions={vi.fn()}
      />,
    )

    const title = screen.getByRole('heading', { level: 3, name: 'Plan incendie' })
    const actionsButton = screen.getByRole('button', { name: 'Actions du plan d’action' })
    const metaRow = actionsButton.parentElement?.parentElement

    expect(screen.getByText('Restaurant')).toBeTruthy()
    expect(metaRow?.className).toContain('items-center')
    expect(metaRow?.contains(actionsButton)).toBe(true)
    expect(metaRow?.nextElementSibling).toBe(title)
  })

  it('keeps relative time and actions on the same row as badges with title below', () => {
    render(
      <ActionPlanExecutionFeedCard
        item={buildFeedItem({
          signal_summary: {
            affected_business_unit_key: 'hotel',
            affected_business_unit_label: 'Hôtel',
            responsible_business_unit_key: 'linge',
            responsible_business_unit_label: 'Linge',
            activity_subject_normalized_name: null,
            activity_subject_label: null,
          },
        })}
        onSelect={onSelect}
        onOpenActions={vi.fn()}
      />,
    )

    const title = screen.getByRole('heading', { level: 3, name: 'Plan incendie' })
    const actionsButton = screen.getByRole('button', { name: 'Actions du plan d’action' })
    const metaRow = actionsButton.parentElement?.parentElement

    expect(screen.getByText('Linge')).toBeTruthy()
    expect(screen.getByText('Restaurant')).toBeTruthy()
    expect(metaRow?.className).toContain('items-center')
    expect(metaRow?.contains(actionsButton)).toBe(true)
    expect(metaRow?.nextElementSibling).toBe(title)
  })

  it('shows pinned badge to the left of status badge when is_pinned is true', () => {
    render(
      <ActionPlanExecutionFeedCard
        item={buildFeedItem({ is_pinned: true })}
        onSelect={onSelect}
      />,
    )

    const pinnedBadge = screen.getByText('Épinglé')
    const statusBadge = screen.getByText('En cours')

    expect(pinnedBadge).toBeTruthy()
    expect(
      pinnedBadge.compareDocumentPosition(statusBadge) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy()
  })

  it('hides pinned badge when is_pinned is false', () => {
    render(<ActionPlanExecutionFeedCard item={buildFeedItem({ is_pinned: false })} onSelect={onSelect} />)

    expect(screen.queryByText('Épinglé')).toBeNull()
    expect(screen.getByText('En cours')).toBeTruthy()
  })

  it('hides pinned badge on pending validation cards', () => {
    render(
      <ActionPlanExecutionFeedCard
        item={buildFeedItem({ status: 'pending_validation', is_pinned: true })}
        onSelect={onSelect}
      />,
    )

    expect(screen.queryByText('Épinglé')).toBeNull()
  })

  it('shows actions menu when can_pin is true', () => {
    const onOpenActions = vi.fn()
    render(
      <ActionPlanExecutionFeedCard
        item={buildFeedItem()}
        onSelect={onSelect}
        onOpenActions={onOpenActions}
      />,
    )

    fireEvent.click(screen.getByLabelText('Actions du plan d’action'))

    expect(onOpenActions).toHaveBeenCalled()
    expect(onSelect).not.toHaveBeenCalled()
  })

  it('shows a single actions button on pending validation cards', () => {
    const onOpenActions = vi.fn()
    render(
      <ActionPlanExecutionFeedCard
        item={buildFeedItem({ status: 'pending_validation' })}
        onSelect={onSelect}
        onOpenActions={onOpenActions}
      />,
    )

    expect(
      screen.getAllByRole('button', { name: 'Actions du plan d’action' }),
    ).toHaveLength(1)
  })

  it('keeps time and actions on the pending validation banner row', () => {
    render(
      <ActionPlanExecutionFeedCard
        item={buildFeedItem({ status: 'pending_validation' })}
        onSelect={onSelect}
        onOpenActions={vi.fn()}
      />,
    )

    const bannerLabel = screen.getByText('En attente de validation')
    const actionsButton = screen.getByRole('button', { name: 'Actions du plan d’action' })
    const bannerRow = bannerLabel.parentElement?.parentElement

    expect(bannerRow?.className).toContain('justify-between')
    expect(bannerRow?.contains(actionsButton)).toBe(true)
    expect(screen.getByText('Restaurant')).toBeTruthy()
    expect(screen.getByRole('heading', { level: 3, name: 'Plan incendie' })).toBeTruthy()
  })

  it('opens actions sheet from pending validation banner without navigating', () => {
    const onOpenActions = vi.fn()
    render(
      <ActionPlanExecutionFeedCard
        item={buildFeedItem({ status: 'pending_validation' })}
        onSelect={onSelect}
        onOpenActions={onOpenActions}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Actions du plan d’action' }))

    expect(onOpenActions).toHaveBeenCalledWith(
      expect.objectContaining({ id: 'execution-1', status: 'pending_validation' }),
    )
    expect(onSelect).not.toHaveBeenCalled()
  })
})
