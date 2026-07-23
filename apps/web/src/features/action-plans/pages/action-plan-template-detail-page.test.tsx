// @vitest-environment jsdom

import { createElement, type ReactNode } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { ActionPlanDetail } from '@/features/action-plans/types'

import { notifySuccess } from '@/lib/success-toast'

import { ActionPlanTemplateDetailPage } from './action-plan-template-detail-page'
import * as catalogPlanningSubmit from '../lib/action-plan-catalog-planning-submit'

vi.mock('@/lib/success-toast', async () => {
  const actual = await vi.importActual<typeof import('@/lib/success-toast')>('@/lib/success-toast')
  return {
    ...actual,
    notifySuccess: vi.fn(),
  }
})

function renderPage(ui: ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(createElement(QueryClientProvider, { client: queryClient }, ui))
}

const detailQueryMock = vi.fn()
const navigateMock = vi.fn()
const activateMutationMock = vi.fn()
const deactivateMutationMock = vi.fn()
const planningMutationMock = vi.fn()

function buildPlan(overrides: Partial<ActionPlanDetail> = {}): ActionPlanDetail {
  return {
    id: 'plan-1',
    title: 'Plan catalogue',
    description: 'Description',
    catalog_status: 'active',
    pilot_business_unit: { id: 'bu-1', specific_name: 'Restaurant', instance_description: '', active: true, generic: { key: 'restaurant', label: 'Restaurant', description: '', unit_type: 'dedicated' } },
    task_count: 1,
    involved_pole_count: 1,
    created_at: '2026-06-30T08:00:00Z',
    updated_at: '2026-06-30T10:00:00Z',
    created_by_id: 'member-1',
    created_by_display_name: 'Alice',
    requires_validation: true,
    is_reusable: true,
    tasks: [
      {
        id: 'task-1',
        task: 'Contrôler la température',
        description: 'Frigo',
        deadline_at: '2026-07-08T10:00:00Z',
        assigned_membership_id: 'member-2',
        assigned_display_name: 'Bob',
        position: 1,
        business_unit: { id: 'bu-1', specific_name: 'Restaurant', instance_description: '', active: true, generic: { key: 'restaurant', label: 'Restaurant', description: '', unit_type: 'dedicated' } },
      },
    ],
    permission_hints: {
      can_update: true,
      can_activate: false,
      can_deactivate: true,
      can_delete: false,
      can_use: true,
      can_schedule: true,
    },
    ...overrides,
  }
}

vi.mock('@/app/app-routes', () => ({
  useAppRoute: () => ({
    navigate: navigateMock,
    route: { kind: 'action-plan-template-detail', actionPlanId: 'plan-1' },
  }),
}))

vi.mock('@/app/auth-provider', () => ({
  useAuth: () => ({
    activeMembership: {
      establishment_id: 'est-1',
      id: 'membership-1',
      role: 'manager',
    },
    bootstrap: {
      user: { username: 'manager_user' },
    },
  }),
}))

vi.mock('../lib/action-plan-planning-submission-intent', async (importOriginal) => {
  const actual =
    await importOriginal<typeof import('../lib/action-plan-planning-submission-intent')>()
  return {
    ...actual,
    resolvePlanningSubmissionIntent: vi.fn(
      async (options: { body: { items: unknown[] } }) => ({
        submissionId: 'sub-fixed',
        requestHash: 'hash',
        itemIds: options.body.items.map((_, index) => `item-fixed-${index}`),
      }),
    ),
    clearPlanningSubmissionIntent: vi.fn(),
  }
})

vi.mock('../hooks', () => ({
  useActionPlanDetailQuery: () => detailQueryMock(),
  useActivateActionPlanMutation: () => activateMutationMock(),
  useDeactivateActionPlanMutation: () => deactivateMutationMock(),
  useSubmitActionPlanPlanningMutation: () => planningMutationMock(),
  deleteActionPlanMutationKey: (establishmentId: string, actionPlanId: string) =>
    ['action-plans', 'delete', establishmentId, actionPlanId] as const,
}))

describe('ActionPlanTemplateDetailPage', () => {
  beforeEach(() => {
    detailQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: buildPlan(),
      refetch: vi.fn(),
    })
    activateMutationMock.mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    })
    deactivateMutationMock.mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    })
    planningMutationMock.mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    })
  })

  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
    vi.restoreAllMocks()
  })

  it('renders read-only template detail with execution action', () => {
    renderPage(createElement(ActionPlanTemplateDetailPage, { actionPlanId: 'plan-1' }))

    expect(screen.getByRole('heading', { name: 'Plan catalogue' })).toBeTruthy()
    expect(screen.getByText('Contrôler la température')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Exécution' })).toBeTruthy()
    expect(screen.queryByRole('textbox')).toBeNull()
    expect(screen.queryByText('Actif')).toBeNull()
  })

  it('renders deactivate in header card and execution in sticky footer', () => {
    renderPage(createElement(ActionPlanTemplateDetailPage, { actionPlanId: 'plan-1' }))

    const headerCard = screen.getByRole('heading', { name: 'Plan catalogue' }).parentElement
    const deactivateButton = screen.getByRole('button', { name: 'Désactiver' })
    const executionButton = screen.getByRole('button', { name: 'Exécution' })

    expect(headerCard).toBeTruthy()
    expect(headerCard!.contains(deactivateButton)).toBe(true)
    expect(deactivateButton.closest('footer')).toBeNull()
    expect(executionButton.closest('footer')).toBeTruthy()
    expect(executionButton.className).toContain('bg-[#114660]')
    expect(screen.queryByRole('button', { name: 'Activer' })).toBeNull()
    expect(screen.queryByText('Activer dans la bibliothèque')).toBeNull()
  })

  it('renders activate in header card for inactive plan', () => {
    detailQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: buildPlan({
        catalog_status: 'inactive',
        permission_hints: {
          can_update: true,
          can_activate: true,
          can_deactivate: false,
          can_delete: false,
          can_use: true,
          can_schedule: true,
        },
      }),
      refetch: vi.fn(),
    })

    renderPage(createElement(ActionPlanTemplateDetailPage, { actionPlanId: 'plan-1' }))

    const headerCard = screen.getByRole('heading', { name: 'Plan catalogue' }).parentElement
    const activateButton = screen.getByRole('button', { name: 'Activer' })
    const executionButton = screen.getByRole('button', { name: 'Exécution' })

    expect(headerCard).toBeTruthy()
    expect(headerCard!.contains(activateButton)).toBe(true)
    expect(activateButton.closest('footer')).toBeNull()
    expect(activateButton.className).toContain('text-[#1D9E75]')
    expect(screen.queryByRole('button', { name: 'Désactiver' })).toBeNull()
    expect(screen.queryByText('Activer dans la bibliothèque')).toBeNull()
    expect(executionButton.closest('footer')).toBeTruthy()
  })

  it('hides sticky footer when inactive plan cannot be used', () => {
    detailQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: buildPlan({
        catalog_status: 'inactive',
        permission_hints: {
          can_update: true,
          can_activate: true,
          can_deactivate: false,
          can_delete: false,
          can_use: false,
          can_schedule: false,
        },
      }),
      refetch: vi.fn(),
    })

    renderPage(createElement(ActionPlanTemplateDetailPage, { actionPlanId: 'plan-1' }))

    expect(screen.getByRole('button', { name: 'Activer' })).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Exécution' })).toBeNull()
    expect(screen.queryByRole('contentinfo')).toBeNull()
  })

  it('calls activate mutation when activate button is clicked', async () => {
    const activateMutateAsync = vi.fn().mockResolvedValue(undefined)
    activateMutationMock.mockReturnValue({
      mutateAsync: activateMutateAsync,
      isPending: false,
    })
    vi.mocked(notifySuccess).mockClear()
    detailQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: buildPlan({
        catalog_status: 'inactive',
        permission_hints: {
          can_update: true,
          can_activate: true,
          can_deactivate: false,
          can_delete: false,
          can_use: false,
          can_schedule: false,
        },
      }),
      refetch: vi.fn(),
    })

    renderPage(createElement(ActionPlanTemplateDetailPage, { actionPlanId: 'plan-1' }))

    fireEvent.click(screen.getByRole('button', { name: 'Activer' }))

    await vi.waitFor(() => {
      expect(activateMutateAsync).toHaveBeenCalled()
      expect(notifySuccess).toHaveBeenCalledWith({
        message: 'Modèle activé.',
        kind: 'activated',
      })
    })
  })

  it('disables activate button while activation is pending', () => {
    activateMutationMock.mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: true,
    })
    detailQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: buildPlan({
        catalog_status: 'inactive',
        permission_hints: {
          can_update: true,
          can_activate: true,
          can_deactivate: false,
          can_delete: false,
          can_use: false,
          can_schedule: false,
        },
      }),
      refetch: vi.fn(),
    })

    renderPage(createElement(ActionPlanTemplateDetailPage, { actionPlanId: 'plan-1' }))

    expect(screen.getByRole('button', { name: 'Activer' })).toHaveProperty('disabled', true)
  })

  it('opens planning panel and sticky launch actions', () => {
    renderPage(createElement(ActionPlanTemplateDetailPage, { actionPlanId: 'plan-1' }))

    fireEvent.click(screen.getByRole('button', { name: 'Exécution' }))

    expect(screen.getByRole('button', { name: 'Annuler' })).toBeTruthy()
    expect(screen.getByRole('button', { name: "Lancer l'exécution" })).toBeTruthy()
    expect(screen.getByText('Répéter')).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Exécution' })).toBeNull()
  })

  it('hides repeat toggle when schedule is not allowed', () => {
    detailQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: buildPlan({
        permission_hints: {
          can_update: true,
          can_activate: false,
          can_deactivate: true,
          can_delete: false,
          can_use: true,
          can_schedule: false,
        },
      }),
      refetch: vi.fn(),
    })

    renderPage(createElement(ActionPlanTemplateDetailPage, { actionPlanId: 'plan-1' }))

    fireEvent.click(screen.getByRole('button', { name: 'Exécution' }))

    expect(screen.queryByText('Répéter')).toBeNull()
  })

  it('shows launch actions in sticky footer when execution panel is open', () => {
    renderPage(createElement(ActionPlanTemplateDetailPage, { actionPlanId: 'plan-1' }))

    fireEvent.click(screen.getByRole('button', { name: 'Exécution' }))

    const cancelButton = screen.getByRole('button', { name: 'Annuler' })
    const launchButton = screen.getByRole('button', { name: "Lancer l'exécution" })

    expect(cancelButton.closest('footer')).toBeTruthy()
    expect(launchButton.closest('footer')).toBeTruthy()
    expect(launchButton.className).toContain('bg-[#114660]')
    expect(screen.getByText('Planification')).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Exécution' })).toBeNull()
  })

  it('shows static launch label when execution panel is open', () => {
    renderPage(createElement(ActionPlanTemplateDetailPage, { actionPlanId: 'plan-1' }))

    fireEvent.click(screen.getByRole('button', { name: 'Exécution' }))

    expect(screen.getByRole('button', { name: "Lancer l'exécution" })).toBeTruthy()
    expect(
      screen.queryByText('Une exécution ponctuelle sera lancée immédiatement.'),
    ).toBeNull()
  })

  it('shows primary launch action when per-assignee chronology is enabled', () => {
    renderPage(createElement(ActionPlanTemplateDetailPage, { actionPlanId: 'plan-1' }))

    fireEvent.click(screen.getByRole('button', { name: 'Exécution' }))
    fireEvent.click(screen.getByRole('switch', { name: 'Chronologie par assigné' }))

    expect(screen.getByRole('button', { name: 'Annuler' })).toBeTruthy()
    expect(screen.getByRole('button', { name: "Lancer l'exécution" })).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Lancer pour cet assigné' })).toBeNull()
  })

  it('navigates to operational feed after planning success', async () => {
    const planningMutateAsync = vi.fn().mockResolvedValue({
      replayed: false,
      summary: { executions_created: 0, schedules_created: 1 },
      executions: [],
      schedules: [{ item_id: 'i1', id: 's1', primary_membership_id: null, status: 'active' }],
    })
    planningMutationMock.mockReturnValue({
      mutateAsync: planningMutateAsync,
      isPending: false,
    })
    vi.spyOn(catalogPlanningSubmit, 'validateCatalogPlanningDraft').mockReturnValue({})
    vi.spyOn(catalogPlanningSubmit, 'resolveCatalogPlanningSubmit').mockReturnValue({
      kind: 'planning',
      body: {
        submission_id: 'sub-1',
        use_shared_chronology: true,
        items: [
          {
            item_id: 'i1',
            kind: 'schedule',
            end_date: '2026-12-31',
            start_at: '09:00:00',
            end_at: '10:00:00',
            recurrence_days: ['monday'],
            assignees: [],
          },
        ],
      },
    })

    renderPage(createElement(ActionPlanTemplateDetailPage, { actionPlanId: 'plan-1' }))

    fireEvent.click(screen.getByRole('button', { name: 'Exécution' }))
    fireEvent.click(screen.getByRole('button', { name: "Lancer l'exécution" }))

    await vi.waitFor(() => {
      expect(planningMutateAsync).toHaveBeenCalled()
    })

    await vi.waitFor(() => {
      expect(navigateMock).toHaveBeenCalledWith('/execution')
    })
    expect(notifySuccess).toHaveBeenCalledWith({
      message: '1 planification créée.',
      kind: 'created',
    })
  })
})
