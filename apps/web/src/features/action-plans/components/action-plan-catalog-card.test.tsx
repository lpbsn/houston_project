// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { ActionPlanListItem } from '../types'

import { ActionPlanCatalogCard } from './action-plan-catalog-card'

function buildListItem(
  partial: Partial<ActionPlanListItem> & Pick<ActionPlanListItem, 'id'>,
): ActionPlanListItem {
  return {
    title: 'Réassort bar hebdomadaire',
    description: 'Contrôle des stocks et réassort des produits bar.',
    catalog_status: 'active',
    pilot_business_unit: { id: 'bu-1', key: 'bar', label: 'Bar' },
    task_count: 3,
    involved_pole_count: 1,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    permission_hints: {
      can_update: false,
      can_activate: false,
      can_deactivate: false,
      can_use: true,
      can_schedule: false,
    },
    ...partial,
  }
}

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe('ActionPlanCatalogCard', () => {
  it('renders title, description, pole label, and task count', () => {
    render(
      createElement(ActionPlanCatalogCard, {
        item: buildListItem({ id: 'plan-1' }),
        onOpen: vi.fn(),
        onUse: vi.fn(),
      }),
    )

    expect(screen.getByText('Réassort bar hebdomadaire')).toBeTruthy()
    expect(screen.getByText(/Contrôle des stocks/)).toBeTruthy()
    expect(screen.getByText('Bar')).toBeTruthy()
    expect(screen.getByText('3 tâches')).toBeTruthy()
  })

  it('renders use CTA when can_use is true', () => {
    render(
      createElement(ActionPlanCatalogCard, {
        item: buildListItem({ id: 'plan-1' }),
        onOpen: vi.fn(),
        onUse: vi.fn(),
      }),
    )

    expect(screen.getByRole('button', { name: 'Utiliser ce plan' })).toBeTruthy()
  })

  it('hides use CTA when can_use is false', () => {
    render(
      createElement(ActionPlanCatalogCard, {
        item: buildListItem({
          id: 'plan-1',
          permission_hints: {
            can_update: false,
            can_activate: false,
            can_deactivate: false,
            can_use: false,
            can_schedule: false,
          },
        }),
        onOpen: vi.fn(),
        onUse: vi.fn(),
      }),
    )

    expect(screen.queryByRole('button', { name: 'Utiliser ce plan' })).toBeNull()
  })

  it('calls onOpen when the informative zone is clicked', () => {
    const onOpen = vi.fn()

    render(
      createElement(ActionPlanCatalogCard, {
        item: buildListItem({ id: 'plan-1' }),
        onOpen,
        onUse: vi.fn(),
      }),
    )

    fireEvent.click(screen.getByText(/Contrôle des stocks/))

    expect(onOpen).toHaveBeenCalledWith('plan-1')
    expect(onOpen).toHaveBeenCalledTimes(1)
  })

  it('calls onUse when the CTA is clicked without triggering onOpen', () => {
    const onOpen = vi.fn()
    const onUse = vi.fn()

    render(
      createElement(ActionPlanCatalogCard, {
        item: buildListItem({ id: 'plan-1' }),
        onOpen,
        onUse,
      }),
    )

    fireEvent.click(screen.getByRole('button', { name: 'Utiliser ce plan' }))

    expect(onUse).toHaveBeenCalledWith('plan-1')
    expect(onOpen).not.toHaveBeenCalled()
  })

  it('shows involved pole count badge when multiple poles are involved', () => {
    render(
      createElement(ActionPlanCatalogCard, {
        item: buildListItem({ id: 'plan-1', involved_pole_count: 3 }),
        onOpen: vi.fn(),
        onUse: vi.fn(),
      }),
    )

    expect(screen.getByText('3 pôles')).toBeTruthy()
  })

  it('shows inactive badge when catalog_status is inactive', () => {
    render(
      createElement(ActionPlanCatalogCard, {
        item: buildListItem({ id: 'plan-1', catalog_status: 'inactive' }),
        onOpen: vi.fn(),
        onUse: vi.fn(),
      }),
    )

    expect(screen.getByText('Inactif')).toBeTruthy()
  })

  it('hides inactive badge when catalog_status is active', () => {
    render(
      createElement(ActionPlanCatalogCard, {
        item: buildListItem({ id: 'plan-1', catalog_status: 'active' }),
        onOpen: vi.fn(),
        onUse: vi.fn(),
      }),
    )

    expect(screen.queryByText('Inactif')).toBeNull()
  })
})
