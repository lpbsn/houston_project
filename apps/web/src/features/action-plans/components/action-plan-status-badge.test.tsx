// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, render } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { ActionPlanStatusBadge } from '@/features/action-plans/components/action-plan-status-badge'

afterEach(() => {
  cleanup()
})

describe('ActionPlanStatusBadge', () => {
  it('renders detail variant in_progress with teal background', () => {
    const { container } = render(
      createElement(ActionPlanStatusBadge, { status: 'in_progress', variant: 'detail' }),
    )

    expect(container.querySelector('.bg-\\[\\#3A7A96\\]')).toBeTruthy()
    expect(container.querySelector('.bg-\\[\\#16435B\\]')).toBeNull()
  })

  it('renders executionHeader variant in_progress with navy background', () => {
    const { container } = render(
      createElement(ActionPlanStatusBadge, { status: 'in_progress', variant: 'executionHeader' }),
    )

    expect(container.querySelector('.bg-\\[\\#16435B\\]')).toBeTruthy()
    expect(container.querySelector('.bg-\\[\\#3A7A96\\]')).toBeNull()
  })

  it('renders executionHeader variant done with green background', () => {
    const { container } = render(
      createElement(ActionPlanStatusBadge, { status: 'done', variant: 'executionHeader' }),
    )

    expect(container.querySelector('.bg-\\[\\#1D9E75\\]')).toBeTruthy()
    expect(container.textContent).toContain('Terminé')
  })

  it('renders Validée when done and validatedAt is set', () => {
    const { container } = render(
      createElement(ActionPlanStatusBadge, {
        status: 'done',
        validatedAt: '2026-07-30T10:00:00Z',
        variant: 'executionHeader',
      }),
    )

    expect(container.querySelector('.bg-\\[\\#1D9E75\\]')).toBeTruthy()
    expect(container.textContent).toContain('Validée')
  })

  it('renders executionHeader variant canceled with gray background', () => {
    const { container } = render(
      createElement(ActionPlanStatusBadge, { status: 'canceled', variant: 'executionHeader' }),
    )

    expect(container.querySelector('.bg-\\[\\#E8E6DF\\]')).toBeTruthy()
  })

  it('renders executionHeader variant pending_validation with amber background', () => {
    const { container } = render(
      createElement(ActionPlanStatusBadge, {
        status: 'pending_validation',
        variant: 'executionHeader',
      }),
    )

    expect(container.querySelector('.bg-\\[\\#EF9F27\\]')).toBeTruthy()
  })
})
