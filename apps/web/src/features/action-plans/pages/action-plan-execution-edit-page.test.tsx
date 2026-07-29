// @vitest-environment jsdom

import { createElement } from 'react'
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { ActionPlanExecutionDetail } from '@/features/action-plans/types'

import { ActionPlanExecutionEditPage } from './action-plan-execution-edit-page'

const detailQueryMock = vi.fn()
const navigateMock = vi.fn()
const submitMock = vi.fn()
const revalidateFrontendMock = vi.fn()
const submitHookState = {
  hasAttemptedSubmit: false,
}

function buildExecution(
  overrides: Partial<ActionPlanExecutionDetail> = {},
): ActionPlanExecutionDetail {
  return {
    id: 'exec-1',
    action_plan_id: 'plan-1',
    status: 'in_progress',
    title: 'Plan nettoyage',
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
    start_at: '2026-07-01T08:00:00.000Z',
    visible_from: '2026-07-01T08:00:00.000Z',
    end_at: '2026-07-01T18:00:00.000Z',
    occurrence_date: null,
    last_activity_at: '2026-07-01T08:00:00.000Z',
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
    created_at: '2026-07-01T07:00:00.000Z',
    updated_at: '2026-07-01T09:00:00.000Z',
    assignees_by_pole: [
      {
        business_unit: {
          id: 'bu-1',
          specific_name: 'Restaurant',
          instance_description: '',
          active: true,
          generic: {
            key: 'restaurant',
            label: 'Restaurant',
            description: '',
            unit_type: 'dedicated',
          },
        },
        assignees: [
          {
            membership_id: 'membership-1',
            display_name: 'Alice',
            start_at: '2026-07-01T08:00:00.000Z',
            visible_from: '2026-07-01T08:00:00.000Z',
            end_at: '2026-07-01T18:00:00.000Z',
          },
        ],
      },
    ],
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

vi.mock('@/app/app-routes', () => ({
  useAppRoute: () => ({
    navigate: navigateMock,
    route: { kind: 'action-plan-execution-edit', executionId: 'exec-1' },
  }),
}))

vi.mock('@/app/auth-provider', () => ({
  useAuth: () => ({
    activeMembership: {
      establishment_id: 'est-1',
      id: 'membership-1',
      role: 'manager',
      scopes: [],
    },
    bootstrap: { user: { username: 'Alice' } },
  }),
}))

vi.mock('@/features/auth/hooks', () => ({
  useBusinessUnitTreeQuery: () => ({
    data: { business_units: [{ id: 'bu-1', specific_name: 'Restaurant' }] },
  }),
}))

vi.mock('../hooks', () => ({
  useActionPlanExecutionDetailQuery: () => detailQueryMock(),
}))

vi.mock('../hooks/use-action-plan-execution-edit-submit', () => ({
  useActionPlanExecutionEditSubmit: () => ({
    submit: submitMock,
    fieldErrors: {},
    submitError: null,
    isSubmitting: false,
    guidanceNonce: 0,
    hasAttemptedSubmit: submitHookState.hasAttemptedSubmit,
    revalidateFrontend: revalidateFrontendMock,
    clearApiFieldError: vi.fn(),
  }),
}))

describe('ActionPlanExecutionEditPage guards', () => {
  beforeEach(() => {
    submitHookState.hasAttemptedSubmit = false
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

  it('blocks edit when can_update is false', () => {
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

    render(createElement(ActionPlanExecutionEditPage, { executionId: 'exec-1' }))

    expect(screen.queryByRole('button', { name: 'Enregistrer les modifications' })).toBeNull()
  })

  it('blocks edit when execution is not in_progress', () => {
    detailQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: buildExecution({ status: 'done' }),
      refetch: vi.fn(),
    })

    render(createElement(ActionPlanExecutionEditPage, { executionId: 'exec-1' }))

    expect(screen.queryByRole('button', { name: 'Enregistrer les modifications' })).toBeNull()
  })

  it('renders edit form when update is allowed for in_progress execution', async () => {
    render(createElement(ActionPlanExecutionEditPage, { executionId: 'exec-1' }))

    expect(
      await screen.findByRole('button', { name: 'Enregistrer les modifications' }),
    ).toBeTruthy()
  })

  it('keeps local draft edits when detail refetch returns a newer updated_at', async () => {
    let execution = buildExecution({ title: 'Titre serveur' })
    detailQueryMock.mockImplementation(() => ({
      isLoading: false,
      isError: false,
      data: execution,
      refetch: vi.fn(),
    }))

    const { rerender } = render(
      createElement(ActionPlanExecutionEditPage, { executionId: 'exec-1' }),
    )

    const titleInput = await screen.findByDisplayValue('Titre serveur')
    fireEvent.change(titleInput, { target: { value: 'Titre local' } })
    expect(screen.getByDisplayValue('Titre local')).toBeTruthy()

    execution = buildExecution({
      title: 'Titre concurrent',
      updated_at: '2026-07-01T10:00:00.000Z',
    })
    rerender(createElement(ActionPlanExecutionEditPage, { executionId: 'exec-1' }))

    expect(screen.getByDisplayValue('Titre local')).toBeTruthy()
    expect(screen.queryByDisplayValue('Titre concurrent')).toBeNull()
  })

  it('keeps both patches from the same batch and revalidates the final form', async () => {
    submitHookState.hasAttemptedSubmit = true
    detailQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: buildExecution({ title: 'Titre initial', description: 'Desc initiale' }),
      refetch: vi.fn(),
    })

    render(createElement(ActionPlanExecutionEditPage, { executionId: 'exec-1' }))

    const titleInput = await screen.findByDisplayValue('Titre initial')
    const descriptionInput = screen.getByDisplayValue('Desc initiale')

    act(() => {
      fireEvent.change(titleInput, { target: { value: 'Titre batch' } })
      fireEvent.change(descriptionInput, { target: { value: 'Desc batch' } })
    })

    expect(screen.getByDisplayValue('Titre batch')).toBeTruthy()
    expect(screen.getByDisplayValue('Desc batch')).toBeTruthy()

    await waitFor(() => {
      expect(
        revalidateFrontendMock.mock.calls.some(
          ([values]) =>
            values.title === 'Titre batch' && values.description === 'Desc batch',
        ),
      ).toBe(true)
    })
  })
})
