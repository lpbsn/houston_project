// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ActionPlanExecutionTaskFilters } from '@/features/action-plans/components/action-plan-execution-task-filters'

afterEach(() => {
  cleanup()
})

describe('ActionPlanExecutionTaskFilters', () => {
  const poles = [
    { businessUnitId: 'bu-1', label: 'Restaurant' },
    { businessUnitId: 'bu-2', label: 'Maintenance' },
  ]

  it('renders Tous and one pill per pole', () => {
    render(
      createElement(ActionPlanExecutionTaskFilters, {
        poles,
        selectedPoleId: null,
        onSelectedPoleIdChange: vi.fn(),
      }),
    )

    expect(screen.getByRole('group', { name: 'Filtrer les tâches par pôle' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Tous' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Restaurant' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Maintenance' })).toBeTruthy()
  })

  it('calls onSelectedPoleIdChange with pole id or null', () => {
    const onSelectedPoleIdChange = vi.fn()

    render(
      createElement(ActionPlanExecutionTaskFilters, {
        poles,
        selectedPoleId: null,
        onSelectedPoleIdChange,
      }),
    )

    fireEvent.click(screen.getByRole('button', { name: 'Maintenance' }))
    expect(onSelectedPoleIdChange).toHaveBeenCalledWith('bu-2')

    fireEvent.click(screen.getByRole('button', { name: 'Tous' }))
    expect(onSelectedPoleIdChange).toHaveBeenCalledWith(null)
  })

  it('marks the selected pill as pressed', () => {
    render(
      createElement(ActionPlanExecutionTaskFilters, {
        poles,
        selectedPoleId: 'bu-1',
        onSelectedPoleIdChange: vi.fn(),
      }),
    )

    expect(screen.getByRole('button', { name: 'Tous' }).getAttribute('aria-pressed')).toBe('false')
    expect(screen.getByRole('button', { name: 'Restaurant' }).getAttribute('aria-pressed')).toBe(
      'true',
    )
    expect(screen.getByRole('button', { name: 'Maintenance' }).getAttribute('aria-pressed')).toBe(
      'false',
    )
  })
})
