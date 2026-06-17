// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ChecklistTemplateDetailPage } from './checklist-template-detail-page'

const navigate = vi.fn()
const scheduleMutateAsync = vi.fn()
const scrollIntoView = vi.fn()

const { templateDetailState, scheduleMutationState } = vi.hoisted(() => ({
  templateDetailState: {
    current: {
      id: 'tpl-1',
      title: 'Routine ouverture',
      description: 'Desc',
      status: 'active',
      business_unit: { id: 'bu-1', key: 'rooftop', label: 'Rooftop' },
      task_count: 1,
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
      permission_hints: {
        can_update: true,
        can_manage_tasks: false,
        can_activate: false,
        can_deactivate: true,
        can_delete: true,
        can_create_assignment: true,
        can_launch_execution: true,
        can_assign_to_others: true,
        can_use_template: true,
      },
      tasks: [{ id: 'task-1', task: 'Vérifier stock', position: 1 }],
    },
  },
  scheduleMutationState: {
    isPending: false,
  },
}))

vi.mock('@/app/app-routes', () => ({
  useAppRoute: () => ({ navigate }),
}))

vi.mock('@/app/auth-provider', () => ({
  useAuth: () => ({
    activeMembership: {
      id: 'member-1',
      establishment_id: 'est-1',
      role: 'manager',
    },
    bootstrap: {
      user: { username: 'manager.user' },
    },
  }),
}))

vi.mock('@/features/checklists/hooks', () => ({
  useChecklistTemplateDetailQuery: () => ({
    data: templateDetailState.current,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  }),
  useUpdateChecklistTemplateMutation: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
  useChecklistAssignmentsQuery: () => ({
    data: [],
    isLoading: false,
    isError: false,
  }),
  useDeactivateChecklistAssignmentMutation: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
  useScheduleChecklistFromTemplateMutation: () => ({
    mutateAsync: scheduleMutateAsync,
    isPending: scheduleMutationState.isPending,
  }),
}))

vi.mock('@/features/actions/hooks', () => ({
  useEstablishmentUserSearchQuery: () => ({
    data: [],
    isLoading: false,
    isError: false,
    isFetching: false,
  }),
}))

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })

  return render(
    createElement(
      QueryClientProvider,
      { client: queryClient },
      createElement(ChecklistTemplateDetailPage, { templateId: 'tpl-1' }),
    ),
  )
}

async function fillOneShotTimes() {
  fireEvent.click(screen.getByRole('button', { name: 'Début' }))
  fireEvent.click(screen.getAllByRole('button', { name: '09' })[0]!)
  fireEvent.click(screen.getByRole('button', { name: '30' }))
  fireEvent.click(screen.getByRole('button', { name: 'Appliquer' }))

  fireEvent.click(screen.getByRole('button', { name: 'Fin' }))
  fireEvent.click(screen.getAllByRole('button', { name: '10' })[0]!)
  fireEvent.click(screen.getByRole('button', { name: '45' }))
  fireEvent.click(screen.getByRole('button', { name: 'Appliquer' }))
}

async function selectRecurringMonday() {
  fireEvent.click(screen.getByRole('button', { name: 'Récurrence' }))
  fireEvent.click(screen.getByRole('button', { name: 'Lundi' }))
  fireEvent.click(screen.getByRole('button', { name: 'Appliquer' }))
  await waitFor(() => {
    expect(screen.getByText('Fin de la récurrence')).toBeTruthy()
  })
}

describe('ChecklistTemplateDetailPage schedule options', () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ['Date'] })
    vi.setSystemTime(new Date('2026-06-17T10:00:00'))

    navigate.mockReset()
    scheduleMutateAsync.mockReset()
    scrollIntoView.mockReset()
    scheduleMutationState.isPending = false

    templateDetailState.current = {
      id: 'tpl-1',
      title: 'Routine ouverture',
      description: 'Desc',
      status: 'active',
      business_unit: { id: 'bu-1', key: 'rooftop', label: 'Rooftop' },
      task_count: 1,
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
      permission_hints: {
        can_update: true,
        can_manage_tasks: false,
        can_activate: false,
        can_deactivate: true,
        can_delete: true,
        can_create_assignment: true,
        can_launch_execution: true,
        can_assign_to_others: true,
        can_use_template: true,
      },
      tasks: [{ id: 'task-1', task: 'Vérifier stock', position: 1 }],
    }

    scheduleMutateAsync.mockResolvedValue({
      result_type: 'execution',
      execution: { id: 'exec-1' },
      assignment: null,
    })

    Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', {
      configurable: true,
      value: scrollIntoView,
    })
  })

  afterEach(() => {
    vi.useRealTimers()
    cleanup()
  })

  it('renders schedule option rows', () => {
    renderPage()
    expect(screen.getByText('Attribuer à')).toBeTruthy()
    expect(screen.getByText('Début')).toBeTruthy()
    expect(screen.getByText('Fin')).toBeTruthy()
    expect(screen.getByText('Récurrence')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Exécution' })).toBeTruthy()
  })

  it('opens distinct time sheets for Début and Fin', async () => {
    renderPage()

    fireEvent.click(screen.getByRole('button', { name: 'Début' }))
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Début' })).toBeTruthy()
    })
    fireEvent.click(screen.getByRole('button', { name: 'Annuler' }))

    fireEvent.click(screen.getByRole('button', { name: 'Fin' }))
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Fin' })).toBeTruthy()
    })
  })

  it('opens assignee sheet', async () => {
    renderPage()
    fireEvent.click(screen.getByRole('button', { name: 'Attribuer à' }))
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Attribuer à' })).toBeTruthy()
    })
  })

  it('shows recurrence end row after selecting recurrence', async () => {
    renderPage()
    await selectRecurringMonday()

    expect(screen.getByRole('button', { name: 'Créer l’affectation' })).toBeTruthy()
  })

  it('submits one-shot execution payload', async () => {
    renderPage()
    await fillOneShotTimes()
    fireEvent.click(screen.getByRole('button', { name: 'Exécution' }))

    await waitFor(() => {
      expect(scheduleMutateAsync).toHaveBeenCalledWith({
        assigned_to: 'member-1',
        start_at: '09:30:00',
        end_at: '10:45:00',
      })
      expect(navigate).toHaveBeenCalledWith('/checklists/executions/exec-1', { replace: true })
    })
  })

  it('submits recurring assignment payload and shows success feedback', async () => {
    scheduleMutateAsync.mockResolvedValue({
      result_type: 'assignment',
      assignment: { id: 'assign-1' },
      execution: null,
    })

    renderPage()
    await fillOneShotTimes()
    await selectRecurringMonday()

    fireEvent.click(screen.getByRole('button', { name: 'Fin de la récurrence' }))
    const dateSheet = screen.getByRole('dialog', { name: 'Fin de la récurrence' })
    fireEvent.change(within(dateSheet).getByLabelText('Fin de la récurrence'), {
      target: { value: '2026-06-30' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Appliquer' }))

    fireEvent.click(screen.getByRole('button', { name: 'Créer l’affectation' }))

    await waitFor(() => {
      expect(scheduleMutateAsync).toHaveBeenCalledWith({
        assigned_to: 'member-1',
        start_at: '09:30:00',
        end_at: '10:45:00',
        recurrence_days: ['monday'],
        recurrence_end_date: '2026-06-30',
      })
      expect(navigate).not.toHaveBeenCalled()
      expect(screen.getByText('Affectation créée.')).toBeTruthy()
      expect(scrollIntoView).toHaveBeenCalled()
    })
  })

  it('shows API error and keeps CTA available after failure', async () => {
    scheduleMutateAsync.mockRejectedValue(new Error('Erreur serveur'))

    renderPage()
    await fillOneShotTimes()
    fireEvent.click(screen.getByRole('button', { name: 'Exécution' }))

    await waitFor(() => {
      expect(screen.getByText('Erreur serveur')).toBeTruthy()
    })

    const cta = screen.getByRole('button', { name: 'Exécution' })
    expect(cta.hasAttribute('disabled')).toBe(false)
  })

  it('disables one-shot CTA when launch execution is forbidden', () => {
    templateDetailState.current = {
      ...templateDetailState.current,
      permission_hints: {
        ...templateDetailState.current.permission_hints,
        can_launch_execution: false,
        can_create_assignment: true,
      },
    }

    renderPage()

    const cta = screen.getByRole('button', { name: 'Exécution' })
    expect(cta.hasAttribute('disabled')).toBe(true)
    expect(
      screen.getByText('Vous ne pouvez pas lancer une exécution ponctuelle.'),
    ).toBeTruthy()
  })

  it('disables recurrence row when assignment creation is forbidden', () => {
    templateDetailState.current = {
      ...templateDetailState.current,
      permission_hints: {
        ...templateDetailState.current.permission_hints,
        can_launch_execution: true,
        can_create_assignment: false,
      },
    }

    renderPage()

    expect(screen.queryByRole('button', { name: 'Récurrence' })).toBeNull()
    const cta = screen.getByRole('button', { name: 'Exécution' })
    expect(cta.hasAttribute('disabled')).toBe(false)
  })

  it('shows inline validation for missing recurrence end date', async () => {
    renderPage()
    await fillOneShotTimes()
    await selectRecurringMonday()

    fireEvent.click(screen.getByRole('button', { name: 'Créer l’affectation' }))

    await waitFor(() => {
      expect(screen.getByText('La fin de la récurrence est obligatoire.')).toBeTruthy()
      expect(scheduleMutateAsync).not.toHaveBeenCalled()
    })
  })

  it('shows inline validation for past recurrence end date', async () => {
    renderPage()
    await fillOneShotTimes()
    await selectRecurringMonday()

    fireEvent.click(screen.getByRole('button', { name: 'Fin de la récurrence' }))
    const dateSheet = screen.getByRole('dialog', { name: 'Fin de la récurrence' })
    fireEvent.change(within(dateSheet).getByLabelText('Fin de la récurrence'), {
      target: { value: '2026-06-10' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Appliquer' }))

    fireEvent.click(screen.getByRole('button', { name: 'Créer l’affectation' }))

    await waitFor(() => {
      expect(
        screen.getByText('La fin de la récurrence ne peut pas être dans le passé.'),
      ).toBeTruthy()
      expect(scheduleMutateAsync).not.toHaveBeenCalled()
    })
  })

  it('shows inline validation when end time is before start time', async () => {
    renderPage()

    fireEvent.click(screen.getByRole('button', { name: 'Début' }))
    fireEvent.click(screen.getAllByRole('button', { name: '09' })[0]!)
    fireEvent.click(screen.getAllByRole('button', { name: '30' })[0]!)
    fireEvent.click(screen.getByRole('button', { name: 'Appliquer' }))

    fireEvent.click(screen.getByRole('button', { name: 'Fin' }))
    fireEvent.click(screen.getAllByRole('button', { name: '09' })[0]!)
    fireEvent.click(screen.getAllByRole('button', { name: '00' })[0]!)
    fireEvent.click(screen.getByRole('button', { name: 'Appliquer' }))

    fireEvent.click(screen.getByRole('button', { name: 'Exécution' }))

    await waitFor(() => {
      expect(
        screen.getByText('L’heure de fin doit être postérieure à l’heure de début.'),
      ).toBeTruthy()
      expect(scheduleMutateAsync).not.toHaveBeenCalled()
    })
  })
})
