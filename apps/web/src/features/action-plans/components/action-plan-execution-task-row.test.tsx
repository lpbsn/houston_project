// @vitest-environment jsdom

import { createElement, type ComponentProps } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ActionPlanExecutionTaskRow } from '@/features/action-plans/components/action-plan-execution-task-row'
import type { ActionPlanTaskExecution } from '@/features/action-plans/types'

function buildTask(overrides: Partial<ActionPlanTaskExecution> = {}): ActionPlanTaskExecution {
  return {
    id: 'task-1',
    task: 'Nettoyer la terrasse',
    description: '',
    deadline_at: null,
    assigned_membership_id: null,
    assigned_display_name: null,
    position: 1,
    status: 'pending',
    business_unit: { id: 'bu-1', key: 'restaurant', label: 'Restaurant' },
    observation_id: null,
    skipped_reason: null,
    completed_at: null,
    skipped_at: null,
    observation_created_at: null,
    permission_hints: {
      can_mark_done: true,
      can_unmark_done: false,
      can_skip: true,
      can_create_observation: true,
    },
    ...overrides,
  } as ActionPlanTaskExecution
}

function renderRow(
  props: Partial<ComponentProps<typeof ActionPlanExecutionTaskRow>> = {},
) {
  const onMarkDone = vi.fn()
  const onUnmarkDone = vi.fn()
  const onOpenActions = vi.fn()

  render(
    createElement(ActionPlanExecutionTaskRow, {
      task: buildTask(),
      canShowMarkDone: true,
      canShowUnmarkDone: false,
      canShowSecondaryActions: true,
      isMutationPending: false,
      onMarkDone,
      onUnmarkDone,
      onOpenActions,
      ...props,
    }),
  )

  return { onMarkDone, onUnmarkDone, onOpenActions }
}

afterEach(() => {
  cleanup()
})

describe('ActionPlanExecutionTaskRow', () => {
  it('does not render inline Observation or Passer buttons', () => {
    renderRow()

    expect(screen.queryByRole('button', { name: 'Observation' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Passer' })).toBeNull()
  })

  it('shows menu button only when secondary actions are allowed', () => {
    const { unmount } = render(
      createElement(ActionPlanExecutionTaskRow, {
        task: buildTask(),
        canShowMarkDone: true,
        canShowUnmarkDone: false,
        canShowSecondaryActions: true,
        isMutationPending: false,
        onMarkDone: vi.fn(),
        onUnmarkDone: vi.fn(),
        onOpenActions: vi.fn(),
      }),
    )

    expect(screen.getByRole('button', { name: 'Actions sur la tâche' })).toBeTruthy()
    unmount()

    render(
      createElement(ActionPlanExecutionTaskRow, {
        task: buildTask(),
        canShowMarkDone: true,
        canShowUnmarkDone: false,
        canShowSecondaryActions: false,
        isMutationPending: false,
        onMarkDone: vi.fn(),
        onUnmarkDone: vi.fn(),
        onOpenActions: vi.fn(),
      }),
    )

    expect(screen.queryByRole('button', { name: 'Actions sur la tâche' })).toBeNull()
  })

  it('calls onOpenActions from menu button', () => {
    const { onOpenActions } = renderRow()

    fireEvent.click(screen.getByRole('button', { name: 'Actions sur la tâche' }))

    expect(onOpenActions).toHaveBeenCalledTimes(1)
  })

  it('shows distinct status labels for terminal states', () => {
    const { unmount } = render(
      createElement(ActionPlanExecutionTaskRow, {
        task: buildTask({ status: 'done' }),
        canShowMarkDone: false,
        canShowUnmarkDone: false,
        canShowSecondaryActions: false,
        isMutationPending: false,
        onMarkDone: vi.fn(),
        onUnmarkDone: vi.fn(),
        onOpenActions: vi.fn(),
      }),
    )
    expect(screen.getByText('Terminée')).toBeTruthy()
    unmount()

    render(
      createElement(ActionPlanExecutionTaskRow, {
        task: buildTask({ status: 'skipped' }),
        canShowMarkDone: false,
        canShowUnmarkDone: false,
        canShowSecondaryActions: false,
        isMutationPending: false,
        onMarkDone: vi.fn(),
        onUnmarkDone: vi.fn(),
        onOpenActions: vi.fn(),
      }),
    )
    expect(screen.getByText('Passée')).toBeTruthy()
    unmount()

    render(
      createElement(ActionPlanExecutionTaskRow, {
        task: buildTask({ status: 'observation_created' }),
        canShowMarkDone: false,
        canShowUnmarkDone: false,
        canShowSecondaryActions: false,
        isMutationPending: false,
        onMarkDone: vi.fn(),
        onUnmarkDone: vi.fn(),
        onOpenActions: vi.fn(),
      }),
    )
    expect(screen.getByText('Observation créée')).toBeTruthy()
  })

  it('calls onMarkDone when pending checkbox is clicked', () => {
    const { onMarkDone } = renderRow()

    fireEvent.click(
      screen.getByRole('button', { name: 'Marquer « Nettoyer la terrasse » comme terminée' }),
    )

    expect(onMarkDone).toHaveBeenCalledTimes(1)
  })

  it('calls onUnmarkDone when done checkbox is clickable', () => {
    const { onUnmarkDone } = renderRow({
      task: buildTask({ status: 'done' }),
      canShowMarkDone: false,
      canShowUnmarkDone: true,
    })

    fireEvent.click(
      screen.getByRole('button', { name: 'Marquer « Nettoyer la terrasse » comme non terminée' }),
    )

    expect(onUnmarkDone).toHaveBeenCalledTimes(1)
  })

  it('does not render clickable unmark button without permission', () => {
    renderRow({
      task: buildTask({ status: 'done' }),
      canShowMarkDone: false,
      canShowUnmarkDone: false,
    })

    expect(
      screen.queryByRole('button', { name: 'Marquer « Nettoyer la terrasse » comme non terminée' }),
    ).toBeNull()
  })

  it('renders description, assignee name, pole, and deadline on separate lines', () => {
    renderRow({
      task: buildTask({
        description: 'Vérifier les étiquettes',
        assigned_display_name: 'Alice Martin',
        deadline_at: '2026-07-07T14:30:00.000Z',
      }),
    })

    expect(screen.getByText('Vérifier les étiquettes')).toBeTruthy()
    expect(screen.getByText('Alice Martin - Restaurant')).toBeTruthy()
    expect(screen.getByText(/Échéance :/)).toBeTruthy()
  })

  it('hides assignee meta when neither assignee nor pole is present', () => {
    renderRow({
      task: buildTask({
        assigned_display_name: null,
        business_unit: { id: 'bu-1', key: 'restaurant', label: '' },
      }),
    })

    expect(screen.queryByText('Restaurant')).toBeNull()
  })

  it('renders terminal status in the bottom-right corner', () => {
    renderRow({
      task: buildTask({
        status: 'done',
        assigned_display_name: 'Alice Martin',
        deadline_at: '2026-07-07T14:30:00.000Z',
      }),
      canShowMarkDone: false,
      canShowUnmarkDone: false,
      canShowSecondaryActions: false,
    })

    const status = screen.getByText('Terminée')
    const deadline = screen.getByText(/Échéance :/)
    const statusRow = status.parentElement?.parentElement

    expect(statusRow).toBe(deadline.parentElement)
    expect(statusRow?.className).toContain('justify-between')
    expect(screen.queryByRole('button', { name: 'Actions sur la tâche' })).toBeNull()
  })

  it('renders task title with text-base font-semibold and circular checkbox', () => {
    const { container } = render(
      createElement(ActionPlanExecutionTaskRow, {
        task: buildTask(),
        canShowMarkDone: true,
        canShowUnmarkDone: false,
        canShowSecondaryActions: true,
        isMutationPending: false,
        onMarkDone: vi.fn(),
        onUnmarkDone: vi.fn(),
        onOpenActions: vi.fn(),
      }),
    )

    const title = screen.getByText('Nettoyer la terrasse')
    expect(title.className).toContain('text-base')
    expect(title.className).toContain('font-semibold')
    expect(container.querySelector('.rounded-full')).toBeTruthy()
  })
})
