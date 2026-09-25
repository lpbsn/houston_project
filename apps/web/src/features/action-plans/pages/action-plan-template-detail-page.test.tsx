// @vitest-environment jsdom

import { createElement, type ReactNode } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { TerrainTopbar } from '@/components/layout/terrain-topbar'
import type { ActionPlanDetail } from '@/features/action-plans/types'

import { notifySuccess } from '@/lib/success-toast'

import { ActionPlanTemplateDetailPage } from './action-plan-template-detail-page'
import * as catalogPlanningSubmit from '../lib/action-plan-catalog-planning-submit'
import {
  formatActionPlanCreatedAtLabel,
  formatActionPlanTaskAssigneePoleLine,
  formatActionPlanTaskDeadlineLabel,
} from '../lib/action-plan-display'

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
    vi.unstubAllEnvs()
    Reflect.deleteProperty(window, 'matchMedia')
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
    const footer = executionButton.closest('footer')

    expect(headerCard).toBeTruthy()
    expect(headerCard!.contains(deactivateButton)).toBe(true)
    expect(deactivateButton.closest('footer')).toBeNull()
    expect(footer).toBeTruthy()
    expect(screen.getAllByRole('button', { name: 'Exécution' })).toHaveLength(1)
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
            all_day: false,
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

  it('offers use and schedule on the template detail without execution comments', () => {
    Object.defineProperty(window, 'matchMedia', {
      configurable: true,
      writable: true,
      value: vi.fn().mockImplementation((query: string) => ({
        matches: query.includes('1024'),
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    })
    vi.stubEnv('VITE_APP_RUNTIME', 'web')

    renderPage(
      createElement(
        'div',
        null,
        createElement(TerrainTopbar, {
          variant: 'detail',
          title: 'Plan',
          hideTitle: true,
          onBack: () => undefined,
        }),
        createElement(ActionPlanTemplateDetailPage, { actionPlanId: 'plan-1' }),
      ),
    )

    expect(screen.getByRole('heading', { name: 'Plan catalogue' })).toBeTruthy()
    expect(screen.getByTestId('action-plan-desktop-description')).toBeTruthy()
    expect(screen.getByText('Contrôler la température')).toBeTruthy()
    expect(screen.getByText('Frigo')).toBeTruthy()
    expect(
      screen.getByText(
        formatActionPlanTaskAssigneePoleLine({
          assigneeDisplayName: 'Bob',
          poleLabel: 'Restaurant',
        }) ?? '',
      ),
    ).toBeTruthy()
    expect(
      screen.getByText(`Échéance : ${formatActionPlanTaskDeadlineLabel('2026-07-08T10:00:00Z')}`),
    ).toBeTruthy()
    expect(screen.queryByRole('checkbox')).toBeNull()
    expect(screen.queryByRole('tab', { name: 'Commentaires' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Exécution' })).toBeNull()

    const tasks = screen.getByTestId('action-plan-desktop-tasks')
    const context = screen.getByTestId('action-plan-desktop-organization')
    const useButton = screen.getByRole('button', { name: 'Utiliser' })
    expect(useButton.compareDocumentPosition(tasks) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(context.compareDocumentPosition(tasks) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Programmer' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Retour' })).toBeTruthy()
    expect(screen.getByText('Date de création')).toBeTruthy()
    expect(screen.getByText('Dernière mise à jour')).toBeTruthy()
    expect(screen.getByText(formatActionPlanCreatedAtLabel('2026-06-30T08:00:00Z') ?? '')).toBeTruthy()
    expect(screen.getByText(formatActionPlanCreatedAtLabel('2026-06-30T10:00:00Z') ?? '')).toBeTruthy()
    const validation = screen.getByText('Validation requise')
    expect(validation.tagName).toBe('SPAN')
    const creator = screen.getByText('Créateur')
    const updated = screen.getByText('Dernière mise à jour')
    const status = screen.getByText('État')
    const statusValue = screen.getByText('Actif')
    const deactivate = screen.getByRole('button', { name: 'Désactiver' })
    expect(validation.compareDocumentPosition(creator) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(updated.compareDocumentPosition(status) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(statusValue.compareDocumentPosition(deactivate) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(validation.parentElement?.contains(deactivate)).toBe(false)

    fireEvent.click(useButton)
    expect(screen.getByRole('button', { name: 'Démarrer' })).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Utiliser' })).toBeNull()
  })

  it('shows the validation badge to a read-only viewer without action rights', () => {
    Object.defineProperty(window, 'matchMedia', {
      configurable: true,
      writable: true,
      value: vi.fn().mockImplementation((query: string) => ({
        matches: query.includes('1024'),
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    })
    vi.stubEnv('VITE_APP_RUNTIME', 'web')
    detailQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: buildPlan({
        requires_validation: true,
        permission_hints: {
          can_update: false,
          can_activate: false,
          can_deactivate: false,
          can_delete: false,
          can_use: false,
          can_schedule: false,
        },
      }),
      refetch: vi.fn(),
    })

    renderPage(createElement(ActionPlanTemplateDetailPage, { actionPlanId: 'plan-1' }))

    const context = screen.getByTestId('action-plan-desktop-organization')
    const validation = screen.getByText('Validation requise')
    expect(validation.tagName).toBe('SPAN')
    expect(context.contains(validation)).toBe(true)
    expect(screen.queryByRole('button', { name: 'Activer' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Désactiver' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Utiliser' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Programmer' })).toBeNull()
  })

  it('places tasks beside context from 1280px', () => {
    Object.defineProperty(window, 'matchMedia', {
      configurable: true,
      writable: true,
      value: vi.fn().mockImplementation((query: string) => {
        const minWidth = /min-width:\s*(\d+)px/.exec(query)
        return {
          matches: minWidth ? 1280 >= Number(minWidth[1]) : false,
          media: query,
          onchange: null,
          addListener: vi.fn(),
          removeListener: vi.fn(),
          addEventListener: vi.fn(),
          removeEventListener: vi.fn(),
          dispatchEvent: vi.fn(),
        }
      }),
    })
    vi.stubEnv('VITE_APP_RUNTIME', 'web')

    renderPage(createElement(ActionPlanTemplateDetailPage, { actionPlanId: 'plan-1' }))

    const main = screen.getByTestId('action-plan-desktop-main')
    const tasks = screen.getByTestId('action-plan-desktop-tasks')
    const context = screen.getByTestId('action-plan-desktop-organization')

    expect(main.contains(screen.getByTestId('action-plan-desktop-title'))).toBe(true)
    expect(main.contains(tasks)).toBe(true)
    expect(main.contains(context)).toBe(false)
    expect(screen.getByTestId('action-plan-desktop-side').contains(context)).toBe(true)
  })

  it('stacks title, description, context, then tasks in one column at 1024px', () => {
    Object.defineProperty(window, 'matchMedia', {
      configurable: true,
      writable: true,
      value: vi.fn().mockImplementation((query: string) => {
        const minWidth = /min-width:\s*(\d+)px/.exec(query)
        return {
          matches: minWidth ? 1024 >= Number(minWidth[1]) : false,
          media: query,
          onchange: null,
          addListener: vi.fn(),
          removeListener: vi.fn(),
          addEventListener: vi.fn(),
          removeEventListener: vi.fn(),
          dispatchEvent: vi.fn(),
        }
      }),
    })
    vi.stubEnv('VITE_APP_RUNTIME', 'web')

    renderPage(createElement(ActionPlanTemplateDetailPage, { actionPlanId: 'plan-1' }))

    const title = screen.getByTestId('action-plan-desktop-title')
    const description = screen.getByTestId('action-plan-desktop-description')
    const context = screen.getByTestId('action-plan-desktop-organization')
    const tasks = screen.getByTestId('action-plan-desktop-tasks')
    const side = screen.getByTestId('action-plan-desktop-side')

    expect(screen.queryByTestId('action-plan-desktop-main')).toBeNull()
    expect(title.compareDocumentPosition(description) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(description.compareDocumentPosition(context) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(context.compareDocumentPosition(tasks) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(side.className).toContain('w-full')
    expect(side.contains(context)).toBe(true)
  })

  it('keeps the execution footer on a large native template detail', () => {
    Object.defineProperty(window, 'matchMedia', {
      configurable: true,
      writable: true,
      value: vi.fn().mockImplementation(() => ({
        matches: true,
        media: '',
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    })
    vi.stubEnv('VITE_APP_RUNTIME', 'native')

    renderPage(createElement(ActionPlanTemplateDetailPage, { actionPlanId: 'plan-1' }))

    expect(screen.getByRole('button', { name: 'Exécution' }).closest('footer')).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Utiliser' })).toBeNull()
  })
})
