// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { ActionPlanTaskDetailLayout } from '@/features/action-plans/components/action-plan-task-detail-layout'

afterEach(() => {
  cleanup()
})

describe('ActionPlanTaskDetailLayout', () => {
  it('renders title row, description, then meta and deadline below a separator', () => {
    const { container } = render(
      createElement(ActionPlanTaskDetailLayout, {
        leading: createElement('span', { 'data-testid': 'leading' }, 'o'),
        title: createElement('span', null, 'Contrôler la terrasse'),
        meta: 'Alice Martin - Restaurant',
        actions: createElement('button', { type: 'button' }, '...'),
        deadline: 'Échéance : 07/07/2026 16:30',
        description: 'Vérifier les étiquettes',
      }),
    )

    const title = screen.getByText('Contrôler la terrasse')
    const meta = screen.getByText('Alice Martin - Restaurant')
    const deadline = screen.getByText('Échéance : 07/07/2026 16:30')
    const description = screen.getByText('Vérifier les étiquettes')
    const leading = screen.getByTestId('leading')
    const titleRow = title.parentElement?.parentElement

    expect(titleRow?.contains(leading)).toBe(true)
    expect(titleRow?.contains(screen.getByRole('button', { name: '...' }))).toBe(true)
    expect(description.compareDocumentPosition(meta) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(meta.parentElement?.className).toContain('border-t')
    expect(deadline.parentElement?.className).toContain('justify-between')
    expect(container.querySelector('.border-t')).toBeTruthy()
  })

  it('renders deadline below the separator when meta is absent', () => {
    render(
      createElement(ActionPlanTaskDetailLayout, {
        title: createElement('span', null, 'Tâche simple'),
        deadline: 'Échéance : 07/07/2026 16:30',
      }),
    )

    const title = screen.getByText('Tâche simple')
    const deadline = screen.getByText('Échéance : 07/07/2026 16:30')

    expect(title.parentElement).not.toBe(deadline.parentElement)
    expect(deadline.parentElement?.parentElement?.className).toContain('border-t')
    expect(screen.queryByRole('button')).toBeNull()
  })

  it('places status in the bottom-right corner of the footer block', () => {
    render(
      createElement(ActionPlanTaskDetailLayout, {
        title: createElement('span', null, 'Tâche terminée'),
        meta: 'Alice Martin - Restaurant',
        deadline: 'Échéance : 07/07/2026 16:30',
        status: createElement('span', null, 'Terminée'),
      }),
    )

    const status = screen.getByText('Terminée')
    const deadline = screen.getByText('Échéance : 07/07/2026 16:30')
    const statusRow = status.parentElement?.parentElement

    expect(statusRow).toBe(deadline.parentElement)
    expect(statusRow?.className).toContain('justify-between')
    expect(status.parentElement?.className).toContain('shrink-0')
  })

  it('omits separator and footer when no meta, deadline, or status', () => {
    const { container } = render(
      createElement(ActionPlanTaskDetailLayout, {
        title: createElement('span', null, 'Tâche simple'),
        description: 'Description',
      }),
    )

    expect(screen.getByText('Tâche simple')).toBeTruthy()
    expect(screen.queryByRole('button')).toBeNull()
    expect(container.querySelector('.border-t')).toBeNull()
  })
})
