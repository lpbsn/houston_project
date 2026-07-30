// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { ActionPlanExecutionFeedItem } from '@/features/action-plans/types'

import { ActionPlanExecutionFeedCard } from './action-plan-execution-feed-card'

const onSelect = vi.fn()
const COUNTDOWN_NOW = Date.parse('2026-07-10T12:00:00Z')

const maintenancePilotBusinessUnit = {
  id: 'bu-maint',
  specific_name: 'Maintenance',
  instance_description: '',
  active: true,
  generic: {
    key: 'maintenance',
    label: 'Maintenance',
    description: '',
    unit_type: 'dedicated' as const,
  },
}

const classificationWithAffectedSummary = {
  affected_business_unit_id: 'bu-restaurant',
  affected_business_unit_key: 'restaurant',
  affected_business_unit_label: 'Restaurant',
  responsible_business_unit_id: 'bu-maintenance',
  responsible_business_unit_key: 'maintenance',
  responsible_business_unit_label: 'Maintenance',
  activity_subject_normalized_name: 'equipements',
  activity_subject_label: 'Équipements d’exploitation',
}

function expectClassificationBadgesWithAffectedLineBelow() {
  const pilotBadge = screen.getByText('Maintenance', { exact: true })
  const classificationBadge = screen.getByText('Maintenance · Équipements d’exploitation')
  const affectedLine = screen.getByText('Concerné : Restaurant')
  const badgesRow = pilotBadge.parentElement

  expect(badgesRow?.className).toContain('items-center')
  expect(badgesRow?.contains(classificationBadge)).toBe(true)
  expect(badgesRow?.contains(affectedLine)).toBe(false)
  expect(affectedLine.parentElement?.contains(badgesRow as Node)).toBe(true)

  return { pilotBadge, classificationBadge, affectedLine, badgesRow }
}

function buildFeedItem(
  overrides: Partial<ActionPlanExecutionFeedItem> = {},
): ActionPlanExecutionFeedItem {
  return {
    id: 'execution-1',
    title: 'Plan incendie',
    description_short: 'Description longue à ne pas afficher',
    status: 'in_progress',
    requires_validation: false,
    validated_at: null,
    pilot_business_unit: { id: 'bu-1', specific_name: 'Restaurant', instance_description: '', active: true, generic: { key: 'restaurant', label: 'Restaurant', description: '', unit_type: 'dedicated' } },
    involved_poles: [
      {
        business_unit: { id: 'bu-2', specific_name: 'Maintenance', instance_description: '', active: true, generic: { key: 'maintenance', label: 'Maintenance', description: '', unit_type: 'dedicated' } },
      },
    ],
    signal_summary: null,
    assignees: [{ membership_id: 'member-1', display_name: 'Alice Martin' }],
    start_at: null,
    end_at: '2026-07-10T16:00:00Z',
    is_overdue: false,
    task_count: 4,
    treated_task_count: 1,
    task_executions: [
      {
        position: 1,
        task: 'Tâche 1',
        status: 'done',
        business_unit: { id: 'bu-1', specific_name: 'Restaurant', instance_description: '', active: true, generic: { key: 'restaurant', label: 'Restaurant', description: '', unit_type: 'dedicated' } },
      },
      {
        position: 2,
        task: 'Tâche 2',
        status: 'pending',
        business_unit: { id: 'bu-1', specific_name: 'Restaurant', instance_description: '', active: true, generic: { key: 'restaurant', label: 'Restaurant', description: '', unit_type: 'dedicated' } },
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
      can_update: false,
      is_pilot_pole_assignee: true,
      can_pin: true,
    },
    ...overrides,
  }
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.spyOn(Date, 'now').mockReturnValue(COUNTDOWN_NOW)
})

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

describe('ActionPlanExecutionFeedCard', () => {
  it('shows in_progress layout with countdown, segmented progress and teal avatar', () => {
    render(<ActionPlanExecutionFeedCard item={buildFeedItem()} onSelect={onSelect} />)

    expect(screen.getByText('Plan incendie')).toBeTruthy()
    expect(screen.getByText('DANS')).toBeTruthy()
    expect(screen.getByText('4h')).toBeTruthy()
    expect(screen.getByText('1/4')).toBeTruthy()
    expect(screen.getByRole('progressbar', { name: 'Progression des tâches : 1/4' })).toBeTruthy()
    expect(screen.queryByText('Tâche 1/4')).toBeNull()
    expect(screen.queryByText(/Échéance :/)).toBeNull()
    expect(screen.getByText('Restaurant')).toBeTruthy()
    expect(screen.getByText('Alice Martin')).toBeTruthy()
    expect(screen.queryByText('En cours')).toBeNull()

    const avatar = document.querySelector('.bg-\\[\\#3A7A96\\]')
    expect(avatar).toBeTruthy()

    expect(screen.queryByText('Description longue à ne pas afficher')).toBeNull()
    expect(screen.queryByText('Tâche 1')).toBeNull()
    expect(screen.queryByText('Tâche 2')).toBeNull()
    expect(screen.queryByText(/Pôles impliqués/)).toBeNull()
  })

  it('shows multi-day countdown for in_progress cards', () => {
    render(
      <ActionPlanExecutionFeedCard
        item={buildFeedItem({ end_at: '2026-07-13T12:00:00Z' })}
        onSelect={onSelect}
      />,
    )

    expect(screen.getByText('3j')).toBeTruthy()
  })

  it('shows infinity when end_at is null on in_progress cards', () => {
    render(
      <ActionPlanExecutionFeedCard item={buildFeedItem({ end_at: null })} onSelect={onSelect} />,
    )

    expect(screen.getByText('∞')).toBeTruthy()
    const sidebar = screen.getByLabelText('Sans échéance')
    expect(sidebar.querySelector('.rounded-full.bg-white\\/20')).toBeTruthy()
    expect(screen.queryByText('DANS')).toBeNull()
    expect(screen.getByText('1/4')).toBeTruthy()
  })

  it('shows overdue 0h without an icon when is_overdue is true and end_at is future', () => {
    render(
      <ActionPlanExecutionFeedCard
        item={buildFeedItem({
          end_at: '2026-07-10T16:00:00Z',
          is_overdue: true,
        })}
        onSelect={onSelect}
      />,
    )

    expect(screen.queryByText('DANS')).toBeNull()
    expect(screen.getByText('RETARD')).toBeTruthy()
    expect(screen.getByText('0h')).toBeTruthy()
    const sidebar = screen.getByLabelText('Échéance dépassée de 0h')
    expect(sidebar.querySelector('svg')).toBeNull()
    expect(document.querySelector('.bg-\\[\\#E24B4A\\]')).toBeTruthy()
  })

  it('shows teal 0h countdown when is_overdue is false and end_at is past', () => {
    render(
      <ActionPlanExecutionFeedCard
        item={buildFeedItem({ end_at: '2026-07-10T11:00:00Z', is_overdue: false })}
        onSelect={onSelect}
      />,
    )

    expect(screen.getByText('DANS')).toBeTruthy()
    expect(screen.getByText('0h')).toBeTruthy()
    expect(screen.queryByLabelText('Échéance dépassée')).toBeNull()
    expect(document.querySelector('.bg-\\[\\#E24B4A\\]')).toBeNull()
    expect(document.querySelector('.bg-\\[\\#3A7A96\\]')).toBeTruthy()
  })

  it('shows overdue duration when is_overdue is true and end_at is past', () => {
    render(
      <ActionPlanExecutionFeedCard
        item={buildFeedItem({ end_at: '2026-07-10T11:00:00Z', is_overdue: true })}
        onSelect={onSelect}
      />,
    )

    expect(screen.queryByText('DANS')).toBeNull()
    expect(screen.getByText('RETARD')).toBeTruthy()
    expect(screen.getByText('1h')).toBeTruthy()
    expect(screen.getByLabelText('Échéance dépassée de 1h')).toBeTruthy()
    expect(document.querySelector('.bg-\\[\\#E24B4A\\]')).toBeTruthy()
  })

  it('omits task progress bar when task_count is zero on in_progress cards', () => {
    render(
      <ActionPlanExecutionFeedCard
        item={buildFeedItem({ task_count: 0, treated_task_count: 0 })}
        onSelect={onSelect}
      />,
    )

    expect(screen.queryByRole('progressbar')).toBeNull()
    expect(screen.queryByText(/\d+\/\d+/)).toBeNull()
  })

  it('shows scheduled layout with DÉBUT countdown and Planifiée status', () => {
    render(
      <ActionPlanExecutionFeedCard
        item={buildFeedItem({
          status: 'scheduled',
          start_at: '2026-07-13T12:00:00Z',
          end_at: null,
          pilot_business_unit: maintenancePilotBusinessUnit,
          signal_summary: classificationWithAffectedSummary,
          permission_hints: {
            can_mark_done: false,
            can_validate: false,
            can_reopen: false,
            can_cancel: true,
            can_update: false,
            is_pilot_pole_assignee: false,
            can_pin: false,
          },
        })}
        onSelect={onSelect}
      />,
    )

    expect(screen.getByText('DÉBUT')).toBeTruthy()
    expect(screen.getByText('3j')).toBeTruthy()
    expect(screen.getByText('Planifiée')).toBeTruthy()
    expect(screen.getByLabelText('Début dans 3j')).toBeTruthy()
    expect(document.querySelector('.bg-\\[\\#8B6914\\]')).toBeTruthy()
    expect(screen.queryByRole('progressbar')).toBeNull()

    const { affectedLine, badgesRow } = expectClassificationBadgesWithAffectedLineBelow()
    const headerRow = badgesRow?.parentElement

    expect(headerRow?.className).toContain('justify-between')
    expect(headerRow?.contains(affectedLine)).toBe(false)
    expect(affectedLine.parentElement?.contains(headerRow as Node)).toBe(true)
  })

  it('keeps Concerné below the badges row on in_progress cards', () => {
    render(
      <ActionPlanExecutionFeedCard
        item={buildFeedItem({
          pilot_business_unit: maintenancePilotBusinessUnit,
          signal_summary: classificationWithAffectedSummary,
        })}
        onSelect={onSelect}
      />,
    )

    const { affectedLine, badgesRow } = expectClassificationBadgesWithAffectedLineBelow()
    const headerRow = badgesRow?.parentElement

    expect(headerRow?.className).toContain('justify-between')
    expect(headerRow?.contains(affectedLine)).toBe(false)
    expect(affectedLine.parentElement?.contains(headerRow as Node)).toBe(true)
  })

  it('keeps Concerné below the badges row on pending validation cards', () => {
    render(
      <ActionPlanExecutionFeedCard
        item={buildFeedItem({
          status: 'pending_validation',
          pilot_business_unit: maintenancePilotBusinessUnit,
          signal_summary: classificationWithAffectedSummary,
        })}
        onSelect={onSelect}
      />,
    )

    expectClassificationBadgesWithAffectedLineBelow()
  })

  it('highlights overdue deadline on pending validation cards', () => {
    render(
      <ActionPlanExecutionFeedCard
        item={buildFeedItem({ status: 'pending_validation', is_overdue: true })}
        onSelect={onSelect}
      />,
    )

    const deadline = screen.getByText(/Échéance :/)
    expect(deadline.className).toContain('text-[#E24B4A]')
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
    expect(document.querySelector('.bg-\\[\\#FCE9B8\\]')).toBeTruthy()
    expect(screen.queryByRole('progressbar')).toBeNull()
  })

  it('navigates to detail on click', () => {
    render(<ActionPlanExecutionFeedCard item={buildFeedItem()} onSelect={onSelect} />)

    fireEvent.click(screen.getByRole('button'))

    expect(onSelect).toHaveBeenCalledWith('execution-1')
  })

  it('shows pilot pole badge on the meta row with title below for in_progress cards', () => {
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
    expect(title).toBeTruthy()
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
    expect(title).toBeTruthy()
  })

  it('shows pinned badge on in_progress cards without status badge', () => {
    render(
      <ActionPlanExecutionFeedCard
        item={buildFeedItem({ is_pinned: true })}
        onSelect={onSelect}
      />,
    )

    expect(screen.getByText('Épinglé')).toBeTruthy()
    expect(screen.queryByText('En cours')).toBeNull()
  })

  it('hides pinned badge when is_pinned is false on in_progress cards', () => {
    render(
      <ActionPlanExecutionFeedCard item={buildFeedItem({ is_pinned: false })} onSelect={onSelect} />,
    )

    expect(screen.queryByText('Épinglé')).toBeNull()
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

  it('renders done card with success sidebar and progress bar', () => {
    render(
      <ActionPlanExecutionFeedCard
        item={buildFeedItem({ status: 'done', treated_task_count: 4, task_count: 4 })}
        onSelect={onSelect}
      />,
    )

    expect(screen.getByLabelText('Terminé')).toBeTruthy()
    expect(document.querySelector('.bg-\\[\\#1D9E75\\]')).toBeTruthy()
    expect(screen.getByRole('progressbar', { name: 'Progression des tâches : 4/4' })).toBeTruthy()
    expect(screen.getByText('4/4')).toBeTruthy()
    expect(screen.queryByText('Tâche 4/4')).toBeNull()
    expect(screen.queryByText('Terminé')).toBeNull()
    expect(screen.queryByRole('status')).toBeNull()
  })

  it('renders canceled card with muted sidebar and progress bar', () => {
    render(
      <ActionPlanExecutionFeedCard
        item={buildFeedItem({ status: 'canceled', treated_task_count: 0, task_count: 2 })}
        onSelect={onSelect}
      />,
    )

    expect(screen.getByLabelText('Annulé')).toBeTruthy()
    expect(document.querySelector('.bg-\\[\\#7D7B75\\]')).toBeTruthy()
    expect(screen.getByRole('progressbar', { name: 'Progression des tâches : 0/2' })).toBeTruthy()
    expect(screen.getByText('0/2')).toBeTruthy()
    expect(screen.queryByText('Annulé')).toBeNull()
  })
})
