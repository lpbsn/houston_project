// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ChecklistExecutionTaskRow } from './checklist-execution-task-row'
import type { ChecklistTaskExecution } from '@/features/checklists/types'

function buildTask(overrides: Partial<ChecklistTaskExecution> = {}): ChecklistTaskExecution {
  return {
    id: 'task-1',
    task: 'Ouvrir la grille',
    position: 0,
    status: 'pending',
    observation_id: null,
    skipped_reason: null,
    completed_at: null,
    skipped_at: null,
    observation_created_at: null,
    ...overrides,
  }
}

const defaultHandlers = {
  onMarkDone: vi.fn(),
  onReport: vi.fn(),
  onSkipRequest: vi.fn(),
}

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe('ChecklistExecutionTaskRow', () => {
  it('renders pending row with actions when canShowActions is true', () => {
    render(
      createElement(ChecklistExecutionTaskRow, {
        task: buildTask(),
        canShowActions: true,
        isMutationPending: false,
        ...defaultHandlers,
      }),
    )

    expect(screen.getByText('Ouvrir la grille')).toBeTruthy()
    expect(
      screen.getByRole('button', { name: /Marquer « Ouvrir la grille » comme terminée/ }),
    ).toBeTruthy()
    expect(
      screen.getByRole('button', { name: /Signaler un problème pour « Ouvrir la grille »/ }),
    ).toBeTruthy()
    expect(
      screen.getByRole('button', { name: /Passer la tâche « Ouvrir la grille »/ }),
    ).toBeTruthy()
  })

  it('hides action buttons when canShowActions is false', () => {
    render(
      createElement(ChecklistExecutionTaskRow, {
        task: buildTask(),
        canShowActions: false,
        isMutationPending: false,
        ...defaultHandlers,
      }),
    )

    expect(screen.queryByRole('button', { name: /Signaler un problème/ })).toBeNull()
    expect(screen.queryByRole('button', { name: /Passer la tâche/ })).toBeNull()
  })

  it('renders done row with strikethrough and no actions', () => {
    render(
      createElement(ChecklistExecutionTaskRow, {
        task: buildTask({ status: 'done' }),
        canShowActions: true,
        isMutationPending: false,
        ...defaultHandlers,
      }),
    )

    expect(screen.getByText('Ouvrir la grille').className).toContain('line-through')
    expect(screen.queryByRole('button', { name: /Signaler/ })).toBeNull()
  })

  it('renders observation_created row as non-interactive without chevron', () => {
    render(
      createElement(ChecklistExecutionTaskRow, {
        task: buildTask({ status: 'observation_created', observation_id: 'obs-1' }),
        canShowActions: true,
        isMutationPending: false,
        ...defaultHandlers,
      }),
    )

    expect(screen.getByText('Observation créée')).toBeTruthy()
    expect(screen.queryByRole('button')).toBeNull()
  })

  it('renders skipped row with Passée label', () => {
    render(
      createElement(ChecklistExecutionTaskRow, {
        task: buildTask({ status: 'skipped' }),
        canShowActions: false,
        isMutationPending: false,
        ...defaultHandlers,
      }),
    )

    expect(screen.getByText('Passée')).toBeTruthy()
  })

  it('disables actions while mutation is pending', () => {
    render(
      createElement(ChecklistExecutionTaskRow, {
        task: buildTask(),
        canShowActions: true,
        isMutationPending: true,
        ...defaultHandlers,
      }),
    )

    expect(
      screen.getByRole('button', { name: /Marquer « Ouvrir la grille » comme terminée/ }),
    ).toHaveProperty('disabled', true)
    expect(
      screen.getByRole('button', { name: /Signaler un problème pour « Ouvrir la grille »/ }),
    ).toHaveProperty('disabled', true)
    expect(
      screen.getByRole('button', { name: /Passer la tâche « Ouvrir la grille »/ }),
    ).toHaveProperty('disabled', true)
  })

  it('calls handlers on user interaction', () => {
    const onMarkDone = vi.fn()
    const onReport = vi.fn()
    const onSkipRequest = vi.fn()

    render(
      createElement(ChecklistExecutionTaskRow, {
        task: buildTask(),
        canShowActions: true,
        isMutationPending: false,
        onMarkDone,
        onReport,
        onSkipRequest,
      }),
    )

    fireEvent.click(
      screen.getByRole('button', { name: /Marquer « Ouvrir la grille » comme terminée/ }),
    )
    fireEvent.click(
      screen.getByRole('button', { name: /Signaler un problème pour « Ouvrir la grille »/ }),
    )
    fireEvent.click(screen.getByRole('button', { name: /Passer la tâche « Ouvrir la grille »/ }))

    expect(onMarkDone).toHaveBeenCalledTimes(1)
    expect(onReport).toHaveBeenCalledTimes(1)
    expect(onSkipRequest).toHaveBeenCalledTimes(1)
  })
})
