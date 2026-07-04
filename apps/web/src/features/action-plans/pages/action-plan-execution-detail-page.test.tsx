// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { ActionPlanExecutionDetail } from '@/features/action-plans/types'

import { ActionPlanExecutionDetailPage } from './action-plan-execution-detail-page'

const detailQueryMock = vi.fn()

const { CommentSectionMock } = vi.hoisted(() => ({
  CommentSectionMock: vi.fn(() => createElement('div', { 'data-testid': 'comment-section' })),
}))

function buildExecution(
  overrides: Partial<ActionPlanExecutionDetail> = {},
): ActionPlanExecutionDetail {
  return {
    id: 'exec-1',
    action_plan_id: 'plan-1',
    status: 'in_progress',
    title: 'Plan nettoyage terrasse',
    description: '',
    requires_validation: false,
    pilot_business_unit: { id: 'bu-1', key: 'restaurant', label: 'Restaurant' },
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
    marked_done_at: null,
    validated_at: null,
    canceled_at: null,
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
      is_pilot_pole_assignee: true,
    },
    ...overrides,
  }
}

vi.mock('@/app/auth-provider', () => ({
  useAuth: () => ({
    activeMembership: {
      establishment_id: 'est-1',
      id: 'membership-1',
    },
  }),
}))

vi.mock('../hooks', () => ({
  useActionPlanExecutionDetailQuery: () => detailQueryMock(),
  useMarkActionPlanExecutionDoneMutation: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
    error: null,
  }),
  useValidateActionPlanExecutionMutation: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
    error: null,
  }),
  useReopenActionPlanExecutionMutation: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
    error: null,
  }),
  useCancelActionPlanExecutionMutation: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
    error: null,
  }),
  useMarkActionPlanTaskDoneMutation: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
    error: null,
  }),
  useSkipActionPlanTaskMutation: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
    error: null,
  }),
  useCreateObservationFromActionPlanTaskMutation: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
    error: null,
  }),
}))

vi.mock('@/features/comments/components/comment-section', () => ({
  CommentSection: CommentSectionMock,
}))

function renderPage() {
  return render(createElement(ActionPlanExecutionDetailPage, { executionId: 'exec-1' }))
}

function getDetailsTab() {
  return screen.getByRole('button', { name: 'Détails' })
}

function getCommentsTab() {
  return screen.getByRole('button', { name: 'Commentaires' })
}

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe('ActionPlanExecutionDetailPage tabs', () => {
  beforeEach(() => {
    detailQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: buildExecution(),
      error: null,
      refetch: vi.fn(),
    })
  })

  it('shows Détails tab by default and does not mount CommentSection', () => {
    renderPage()

    expect(getDetailsTab().getAttribute('aria-pressed')).toBe('true')
    expect(getCommentsTab().getAttribute('aria-pressed')).toBe('false')
    expect(screen.getByText('Plan nettoyage terrasse')).toBeTruthy()
    expect(screen.queryByTestId('comment-section')).toBeNull()
    expect(CommentSectionMock).not.toHaveBeenCalled()
  })

  it('mounts CommentSection on first click on Commentaires', () => {
    renderPage()

    fireEvent.click(getCommentsTab())

    expect(screen.getByTestId('comment-section')).toBeTruthy()
    expect(CommentSectionMock).toHaveBeenCalledWith(
      expect.objectContaining({
        establishmentId: 'est-1',
        targetType: 'action-plan-execution',
        targetId: 'exec-1',
      }),
      undefined,
    )
  })

  it('shows sticky footer only on Détails tab', () => {
    renderPage()

    expect(screen.getByRole('button', { name: 'Marquer terminé' })).toBeTruthy()

    fireEvent.click(getCommentsTab())

    expect(screen.queryByRole('button', { name: 'Marquer terminé' })).toBeNull()
  })
})
