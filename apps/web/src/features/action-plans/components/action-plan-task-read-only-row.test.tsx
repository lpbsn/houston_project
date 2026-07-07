// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { ActionPlanTaskReadOnlyRow } from '@/features/action-plans/components/action-plan-task-read-only-row'
import type { ActionPlanTaskTemplate } from '@/features/action-plans/types'

function buildTask(overrides: Partial<ActionPlanTaskTemplate> = {}): ActionPlanTaskTemplate {
  return {
    id: 'task-1',
    task: 'Contrôler la terrasse',
    description: 'Vérifier les étiquettes',
    deadline_at: '2026-07-07T14:30:00.000Z',
    assigned_membership_id: 'member-1',
    assigned_display_name: 'Alice Martin',
    position: 1,
    business_unit: { id: 'bu-1', key: 'restaurant', label: 'Restaurant' },
    ...overrides,
  }
}

afterEach(() => {
  cleanup()
})

describe('ActionPlanTaskReadOnlyRow', () => {
  it('renders harmonized task detail with assignee, pole, deadline, and description', () => {
    render(createElement(ActionPlanTaskReadOnlyRow, { task: buildTask() }))

    expect(screen.getByText('Contrôler la terrasse')).toBeTruthy()
    expect(screen.getByText('Alice Martin - Restaurant')).toBeTruthy()
    expect(screen.getByText(/Échéance :/)).toBeTruthy()
    expect(screen.getByText('Vérifier les étiquettes')).toBeTruthy()
    expect(screen.queryByRole('button')).toBeNull()
  })

  it('renders deadline below the separator when assignee and pole are absent', () => {
    render(
      createElement(ActionPlanTaskReadOnlyRow, {
        task: buildTask({
          assigned_display_name: null,
          business_unit: { id: 'bu-1', key: 'restaurant', label: '' },
        }),
      }),
    )

    const title = screen.getByText('Contrôler la terrasse')
    const deadline = screen.getByText(/Échéance :/)

    expect(title.parentElement).not.toBe(deadline.parentElement)
    expect(deadline.parentElement?.parentElement?.className).toContain('border-t')
  })
})
