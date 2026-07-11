// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { ActionPlanDetail } from '@/features/action-plans/types'

import { ActionPlanTemplateDetailTopbarTrailing } from './action-plan-template-detail-topbar-trailing'

const detailQueryMock = vi.fn()
const navigateMock = vi.fn()

function buildPlan(overrides: Partial<ActionPlanDetail> = {}): ActionPlanDetail {
  return {
    id: 'plan-1',
    title: 'Plan catalogue',
    description: 'Description',
    catalog_status: 'active',
    pilot_business_unit: { id: 'bu-1', key: 'restaurant', label: 'Restaurant' },
    task_count: 1,
    involved_pole_count: 1,
    created_at: '2026-06-30T08:00:00Z',
    updated_at: '2026-06-30T10:00:00Z',
    created_by_id: 'member-1',
    created_by_display_name: 'Alice',
    requires_validation: false,
    is_reusable: true,
    tasks: [],
    permission_hints: {
      can_update: true,
      can_activate: false,
      can_deactivate: false,
      can_use: true,
      can_schedule: true,
    },
    ...overrides,
  }
}

vi.mock('../hooks', () => ({
  useActionPlanDetailQuery: () => detailQueryMock(),
}))

describe('ActionPlanTemplateDetailTopbarTrailing', () => {
  beforeEach(() => {
    detailQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: buildPlan(),
      refetch: vi.fn(),
    })
  })

  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  it('shows edit pencil when can_update is granted', () => {
    render(
      createElement(ActionPlanTemplateDetailTopbarTrailing, {
        establishmentId: 'est-1',
        actionPlanId: 'plan-1',
        onNavigate: navigateMock,
      }),
    )

    expect(screen.getByRole('button', { name: 'Modifier' })).toBeTruthy()
  })

  it('hides edit pencil when can_update is false', () => {
    detailQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: buildPlan({
        permission_hints: {
          can_update: false,
          can_activate: false,
          can_deactivate: false,
          can_use: true,
          can_schedule: true,
        },
      }),
      refetch: vi.fn(),
    })

    render(
      createElement(ActionPlanTemplateDetailTopbarTrailing, {
        establishmentId: 'est-1',
        actionPlanId: 'plan-1',
        onNavigate: navigateMock,
      }),
    )

    expect(screen.queryByRole('button', { name: 'Modifier' })).toBeNull()
  })

  it('navigates to edit route when pencil is clicked', () => {
    render(
      createElement(ActionPlanTemplateDetailTopbarTrailing, {
        establishmentId: 'est-1',
        actionPlanId: 'plan-1',
        onNavigate: navigateMock,
      }),
    )

    fireEvent.click(screen.getByRole('button', { name: 'Modifier' }))

    expect(navigateMock).toHaveBeenCalledWith('/action-plans/plan-1/edit')
  })
})
