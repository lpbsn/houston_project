// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { ChecklistExecutionDetail, ChecklistTaskExecution } from '@/features/checklists/types'
import { formatChecklistDeadlinePillLabel } from '@/features/checklists/lib/checklist-display'

import { ChecklistExecutionDetailPage } from './checklist-execution-detail-page'

const navigate = vi.fn()
const mutateAsyncMarkDone = vi.fn()
const mutateAsyncSkip = vi.fn()
const mutateAsyncCancel = vi.fn()

function buildTask(overrides: Partial<ChecklistTaskExecution> = {}): ChecklistTaskExecution {
  return {
    id: 'task-1',
    task: 'Vérifier les issues',
    position: 0,
    status: 'pending',
    observation_id: null,
    skipped_reason: null,
    completed_at: null,
    skipped_at: null,
    observation_created_at: null,
    ...overrides,
  }
}

function buildExecution(
  overrides: Partial<ChecklistExecutionDetail> = {},
): ChecklistExecutionDetail {
  return {
    id: 'exec-1',
    execution_source: 'template',
    checklist_template_id: 'tpl-1',
    checklist_assignment_id: 'assign-1',
    status: 'in_progress',
    template_title: 'To do ouverture',
    template_description: '',
    business_unit: { id: 'bu-1', key: 'rooftop', label: 'Rooftop' },
    assigned_to_id: 'user-1',
    assigned_to_display_name: 'Staff',
    assigned_by_id: null,
    assigned_by_display_name: null,
    start_at: null,
    visible_from: null,
    end_at: '2026-06-30T10:00:00',
    occurrence_date: null,
    last_activity_at: '2026-06-30T08:00:00',
    started_at: '2026-06-30T08:00:00',
    done_at: null,
    canceled_at: null,
    created_at: '2026-06-30T08:00:00',
    updated_at: '2026-06-30T08:00:00',
    task_executions: [
      buildTask(),
      buildTask({ id: 'task-2', task: 'Désactiver l’alarme', position: 1, status: 'done' }),
    ],
    permission_hints: {
      can_execute_tasks: true,
      can_cancel: true,
    },
    ...overrides,
  }
}

const detailQueryMock = vi.fn()

vi.mock('@/app/app-routes', () => ({
  useAppRoute: () => ({ navigate }),
}))

vi.mock('@/app/auth-provider', () => ({
  useAuth: () => ({
    activeMembership: { establishment_id: 'est-1' },
  }),
}))

vi.mock('@/features/checklists/hooks', () => ({
  useChecklistExecutionDetailQuery: () => detailQueryMock(),
  useCancelChecklistExecutionMutation: () => ({
    mutateAsync: mutateAsyncCancel,
    isPending: false,
  }),
  useMarkChecklistTaskDoneMutation: () => ({
    mutateAsync: mutateAsyncMarkDone,
    isPending: false,
  }),
  useSkipChecklistTaskMutation: () => ({
    mutateAsync: mutateAsyncSkip,
    isPending: false,
  }),
}))

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })

  return render(
    createElement(
      QueryClientProvider,
      { client: queryClient },
      createElement(ChecklistExecutionDetailPage, { executionId: 'exec-1' }),
    ),
  )
}

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe('ChecklistExecutionDetailPage', () => {
  it('renders header with title, business unit, deadline pill and progress', () => {
    detailQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: buildExecution(),
      error: null,
      refetch: vi.fn(),
    })

    renderPage()

    expect(screen.getByRole('heading', { name: 'To do ouverture' })).toBeTruthy()
    expect(screen.getByText('Rooftop')).toBeTruthy()
    expect(screen.getByText(formatChecklistDeadlinePillLabel('2026-06-30T10:00:00')!)).toBeTruthy()
    expect(screen.getByText('1 / 2 points')).toBeTruthy()
    expect(screen.getByText('50%')).toBeTruthy()
  })

  it('navigates to reporting when + is clicked', () => {
    detailQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: buildExecution(),
      error: null,
      refetch: vi.fn(),
    })

    renderPage()

    fireEvent.click(
      screen.getByRole('button', {
        name: /Signaler un problème pour « Vérifier les issues »/,
      }),
    )

    expect(navigate).toHaveBeenCalledWith(
      '/reporting?checklist_execution_id=exec-1&checklist_task_execution_id=task-1',
    )
  })

  it('shows feedback after mark done without optimistic UI change before resolve', async () => {
    let resolveMarkDone: (() => void) | undefined

    mutateAsyncMarkDone.mockImplementation(
      () =>
        new Promise<void>((resolve) => {
          resolveMarkDone = resolve
        }),
    )

    detailQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: buildExecution(),
      error: null,
      refetch: vi.fn(),
    })

    renderPage()

    fireEvent.click(
      screen.getByRole('button', {
        name: /Marquer « Vérifier les issues » comme terminée/,
      }),
    )

    expect(screen.getByText('Vérifier les issues')).toBeTruthy()
    expect(screen.queryByText('Tâche terminée.')).toBeNull()

    resolveMarkDone?.()

    await waitFor(() => {
      expect(screen.getByText('Tâche terminée.')).toBeTruthy()
    })
  })

  it('renders cancel button in document flow when allowed', () => {
    detailQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: buildExecution(),
      error: null,
      refetch: vi.fn(),
    })

    renderPage()

    const cancelButton = screen.getByRole('button', { name: /Annuler l'exécution/ })
    expect(cancelButton).toBeTruthy()
    expect(cancelButton.className).toContain('w-full')
  })
})
