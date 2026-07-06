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
    permission_hints: {
      can_mark_done: true,
      can_validate: false,
      can_reopen: false,
      can_cancel: false,
      is_pilot_pole_assignee: true,
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
    expect(screen.getByText('Tâches 1/4')).toBeTruthy()
    expect(screen.getByText(/Échéance :/)).toBeTruthy()
    expect(screen.getByText('Pôle pilote : Restaurant')).toBeTruthy()
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

    expect(screen.queryByText(/Tâches \d+\/\d+/)).toBeNull()
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
})
