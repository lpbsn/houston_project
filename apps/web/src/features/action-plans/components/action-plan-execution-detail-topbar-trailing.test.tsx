// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { ActionPlanExecutionDetail } from '@/features/action-plans/types'

import { ActionPlanExecutionDetailTopbarTrailing } from './action-plan-execution-detail-topbar-trailing'

const detailQueryMock = vi.fn()
const navigateMock = vi.fn()

function buildExecution(
  overrides: Partial<ActionPlanExecutionDetail> = {},
): ActionPlanExecutionDetail {
  return {
    id: 'exec-1',
    action_plan_id: 'plan-1',
    status: 'in_progress',
    title: 'Plan',
    description: '',
    requires_validation: false,
    pilot_business_unit: {
      id: 'bu-1',
      specific_name: 'Restaurant',
      instance_description: '',
      active: true,
      generic: { key: 'restaurant', label: 'Restaurant', description: '', unit_type: 'dedicated' },
    },
    affected_business_unit: null,
    responsible_business_unit: null,
    activity_subject: null,
    signal_summary: null,
    created_by_id: 'user-1',
    created_by_display_name: 'Alice',
    use_shared_chronology: true,
    start_at: null,
    visible_from: null,
    end_at: null,
    occurrence_date: null,
    last_activity_at: '2026-06-30T10:00:00Z',
    marked_done_by_membership_id: null,
    marked_done_by_display_name: null,
    marked_done_at: null,
    validated_by_membership_id: null,
    validated_by_display_name: null,
    validated_at: null,
    canceled_by_membership_id: null,
    canceled_by_display_name: null,
    canceled_at: null,
    cancel_origin: null,
    reopened_by_membership_id: null,
    reopened_by_display_name: null,
    reopened_at: null,
    started_by_membership_id: null,
    started_by_display_name: null,
    started_at: null,
    reactivated_by_membership_id: null,
    reactivated_by_display_name: null,
    reactivated_at: null,
    created_at: '2026-06-30T08:00:00Z',
    updated_at: '2026-06-30T10:00:00Z',
    assignees_by_pole: [],
    involved_poles: [],
    task_executions: [],
    permission_hints: {
      can_mark_done: true,
      can_validate: false,
      can_reopen: false,
      can_cancel: false,
      can_update: true,
      is_pilot_pole_assignee: true,
      can_pin: false,
    },
    ...overrides,
  }
}

vi.mock('../hooks', () => ({
  useActionPlanExecutionDetailQuery: () => detailQueryMock(),
}))

describe('ActionPlanExecutionDetailTopbarTrailing', () => {
  beforeEach(() => {
    detailQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: buildExecution(),
      refetch: vi.fn(),
    })
  })

  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  it('shows edit pencil when can_update is granted', () => {
    render(
      createElement(ActionPlanExecutionDetailTopbarTrailing, {
        establishmentId: 'est-1',
        executionId: 'exec-1',
        onNavigate: navigateMock,
      }),
    )

    expect(screen.getByRole('button', { name: 'Modifier' })).toBeTruthy()
  })

  it('hides edit pencil when can_update is false', () => {
    detailQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: buildExecution({
        permission_hints: {
          can_mark_done: true,
          can_validate: false,
          can_reopen: false,
          can_cancel: false,
          can_update: false,
          is_pilot_pole_assignee: true,
          can_pin: false,
        },
      }),
      refetch: vi.fn(),
    })

    render(
      createElement(ActionPlanExecutionDetailTopbarTrailing, {
        establishmentId: 'est-1',
        executionId: 'exec-1',
        onNavigate: navigateMock,
      }),
    )

    expect(screen.queryByRole('button', { name: 'Modifier' })).toBeNull()
  })

  it('navigates to execution edit route when pencil is clicked', () => {
    render(
      createElement(ActionPlanExecutionDetailTopbarTrailing, {
        establishmentId: 'est-1',
        executionId: 'exec-1',
        onNavigate: navigateMock,
      }),
    )

    fireEvent.click(screen.getByRole('button', { name: 'Modifier' }))

    expect(navigateMock).toHaveBeenCalledWith('/action-plans/executions/exec-1/edit')
  })
})
