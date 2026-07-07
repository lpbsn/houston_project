// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { ActionPlanExecutionDetail } from '@/features/action-plans/types'

import { ActionPlanExecutionDetailPage } from './action-plan-execution-detail-page'

const detailQueryMock = vi.fn()
const navigateMock = vi.fn()

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
      can_pin: false,
    },
    ...overrides,
  }
}

vi.mock('@/app/app-routes', () => ({
  useAppRoute: () => ({
    navigate: navigateMock,
    route: { kind: 'action-plan-execution-detail', executionId: 'exec-1' },
  }),
}))

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
  useMarkActionPlanTaskPendingMutation: () => ({
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

function buildTaskExecution(
  overrides: Partial<ActionPlanExecutionDetail['task_executions'][number]> &
    Pick<ActionPlanExecutionDetail['task_executions'][number], 'id' | 'task' | 'position' | 'business_unit'>,
): ActionPlanExecutionDetail['task_executions'][number] {
  return {
    description: '',
    deadline_at: null,
    assigned_membership_id: null,
    assigned_display_name: null,
    status: 'pending',
    observation_id: null,
    skipped_reason: null,
    completed_at: null,
    skipped_at: null,
    observation_created_at: null,
    permission_hints: {
      can_mark_done: true,
      can_unmark_done: false,
      can_skip: true,
      can_create_observation: true,
    },
    ...overrides,
  }
}

function buildMultiPoleExecution(): ActionPlanExecutionDetail {
  return buildExecution({
    task_executions: [
      buildTaskExecution({
        id: 'task-1',
        task: 'Contrôler la terrasse',
        position: 1,
        business_unit: { id: 'bu-1', key: 'restaurant', label: 'Restaurant' },
      }),
      buildTaskExecution({
        id: 'task-2',
        task: 'Appeler technicien',
        position: 2,
        business_unit: { id: 'bu-2', key: 'maintenance', label: 'Maintenance' },
      }),
    ],
  })
}

function renderPage() {
  return render(createElement(ActionPlanExecutionDetailPage, { executionId: 'exec-1' }))
}

function getDetailsTab() {
  return screen.getByRole('tab', { name: 'Détails' })
}

function getCommentsTab() {
  return screen.getByRole('tab', { name: 'Commentaires' })
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

    expect(getDetailsTab().getAttribute('aria-selected')).toBe('true')
    expect(getCommentsTab().getAttribute('aria-selected')).toBe('false')
    expect(screen.getByText('Plan nettoyage terrasse')).toBeTruthy()
    expect(screen.getByRole('tabpanel', { name: /détails/i })).toBeTruthy()
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

  it('renders a flat task list without pole section headers', () => {
    detailQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: buildExecution({
        task_executions: [
          {
            id: 'task-1',
            task: 'Contrôler la terrasse',
            description: '',
            deadline_at: null,
            assigned_membership_id: null,
            assigned_display_name: 'Alice Martin',
            position: 1,
            status: 'pending',
            business_unit: { id: 'bu-1', key: 'restaurant', label: 'Restaurant' },
            observation_id: null,
            skipped_reason: null,
            completed_at: null,
            skipped_at: null,
            observation_created_at: null,
            permission_hints: {
              can_mark_done: true,
              can_unmark_done: false,
              can_skip: true,
              can_create_observation: true,
            },
          },
        ],
      }),
      error: null,
      refetch: vi.fn(),
    })

    renderPage()

    expect(screen.getByText('Contrôler la terrasse')).toBeTruthy()
    expect(screen.getByText(/Alice Martin/)).toBeTruthy()
    expect(screen.queryByText('Assignées :')).toBeNull()
    expect(screen.queryByText('Contribution :')).toBeNull()
  })

  it('renders structured detail sections with creator, assignees, and pole summaries', () => {
    detailQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: buildExecution({
        description: 'Vérifier le disjoncteur en local technique.',
        responsible_business_unit: { id: 'bu-2', key: 'maintenance', label: 'Maintenance' },
        activity_subject: {
          id: 'sub-1',
          normalized_name: 'climatisation',
          label: 'Climatisation',
        },
        end_at: '2026-07-07T10:15:00.000Z',
        start_at: '2026-07-07T09:00:00.000Z',
        assignees_by_pole: [
          {
            business_unit: { id: 'bu-1', key: 'restaurant', label: 'Restaurant' },
            assignees: [
              { membership_id: 'membership-1', display_name: 'Jean D.' },
              { membership_id: 'm-2', display_name: 'Paul B.' },
            ],
          },
        ],
        task_executions: [
          {
            id: 'task-1',
            task: 'Contrôler la terrasse',
            description: '',
            deadline_at: null,
            assigned_membership_id: null,
            assigned_display_name: null,
            position: 1,
            status: 'pending',
            business_unit: { id: 'bu-1', key: 'restaurant', label: 'Restaurant' },
            observation_id: null,
            skipped_reason: null,
            completed_at: null,
            skipped_at: null,
            observation_created_at: null,
            permission_hints: {
              can_mark_done: true,
              can_unmark_done: false,
              can_skip: true,
              can_create_observation: true,
            },
          },
          {
            id: 'task-2',
            task: 'Appeler technicien',
            description: '',
            deadline_at: null,
            assigned_membership_id: null,
            assigned_display_name: null,
            position: 2,
            status: 'done',
            business_unit: { id: 'bu-2', key: 'maintenance', label: 'Maintenance' },
            observation_id: null,
            skipped_reason: null,
            completed_at: null,
            skipped_at: null,
            observation_created_at: null,
            permission_hints: {
              can_mark_done: true,
              can_unmark_done: false,
              can_skip: true,
              can_create_observation: true,
            },
          },
        ],
      }),
      error: null,
      refetch: vi.fn(),
    })

    renderPage()

    expect(screen.getByText(/Créé par/)).toBeTruthy()
    expect(screen.getAllByText('Maintenance').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('Climatisation')).toBeTruthy()
    const deadlineLabel = screen.getByText('Deadline')
    const assigneesLabel = screen.getByText('Assignés')
    expect(
      deadlineLabel.compareDocumentPosition(assigneesLabel) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy()
    const assigneesList = screen.getByRole('list', { name: 'Assignés' })
    expect(assigneesList.textContent).toContain('Jean D.')
    expect(assigneesList.textContent).toContain('(vous)')
    expect(screen.getByText('Paul B.')).toBeTruthy()
    expect(screen.getByText('Description')).toBeTruthy()
    expect(screen.getByText('Vérifier le disjoncteur en local technique.')).toBeTruthy()
    expect(screen.getByText('Tâches par pôle')).toBeTruthy()
    expect(screen.getByText(/Pôle pilote :/)).toBeTruthy()
    expect(screen.getByText(/Pôle contributeur :/)).toBeTruthy()
    expect(screen.getByText(/Tâche 0\/1/)).toBeTruthy()
    expect(screen.getByText(/Tâche 1\/1/)).toBeTruthy()
  })

  it('shows linked signal strip and navigates to signal detail', () => {
    detailQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: buildExecution({
        signal_summary: {
          id: 'signal-42',
          title: 'Fuite terrasse',
          status: 'open',
          urgency: 'normal',
          affected_business_unit_key: null,
          affected_business_unit_label: null,
          responsible_business_unit_key: null,
          responsible_business_unit_label: null,
          activity_subject_normalized_name: null,
          activity_subject_label: null,
          location_text: 'Terrasse',
        },
      }),
      error: null,
      refetch: vi.fn(),
    })

    renderPage()

    expect(screen.getByText('Signal lié')).toBeTruthy()
    expect(screen.getByText(/Fuite terrasse/)).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: 'Voir le signal lié' }))

    expect(navigateMock).toHaveBeenCalledWith('/signals/signal-42')
  })
})

describe('ActionPlanExecutionDetailPage pole task filters', () => {
  it('does not render pole filters when tasks belong to a single pole', () => {
    detailQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: buildExecution({
        task_executions: [
          buildTaskExecution({
            id: 'task-1',
            task: 'Contrôler la terrasse',
            position: 1,
            business_unit: { id: 'bu-1', key: 'restaurant', label: 'Restaurant' },
          }),
        ],
      }),
      error: null,
      refetch: vi.fn(),
    })

    renderPage()

    expect(screen.queryByRole('group', { name: 'Filtrer les tâches par pôle' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Tous' })).toBeNull()
  })

  it('renders pole filters for multi-pole executions', () => {
    detailQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: buildMultiPoleExecution(),
      error: null,
      refetch: vi.fn(),
    })

    renderPage()

    expect(screen.getByRole('group', { name: 'Filtrer les tâches par pôle' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Tous' })).toBeTruthy()
    expect(screen.getAllByRole('button', { name: 'Restaurant' }).length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByRole('button', { name: 'Maintenance' }).length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('Contrôler la terrasse')).toBeTruthy()
    expect(screen.getByText('Appeler technicien')).toBeTruthy()
  })

  it('filters visible tasks when a pole pill is selected', () => {
    detailQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: buildMultiPoleExecution(),
      error: null,
      refetch: vi.fn(),
    })

    renderPage()

    fireEvent.click(screen.getByRole('button', { name: 'Maintenance' }))

    expect(screen.queryByText('Contrôler la terrasse')).toBeNull()
    expect(screen.getByText('Appeler technicien')).toBeTruthy()
  })

  it('shows all tasks again when Tous is selected', () => {
    detailQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: buildMultiPoleExecution(),
      error: null,
      refetch: vi.fn(),
    })

    renderPage()

    fireEvent.click(screen.getByRole('button', { name: 'Maintenance' }))
    fireEvent.click(screen.getByRole('button', { name: 'Tous' }))

    expect(screen.getByText('Contrôler la terrasse')).toBeTruthy()
    expect(screen.getByText('Appeler technicien')).toBeTruthy()
  })
})
