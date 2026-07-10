// @vitest-environment jsdom

import { createElement, useEffect } from 'react'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ActionPlanCreatePage } from './action-plan-create-page'

const navigate = vi.fn()
const createMutateAsync = vi.fn()
const signalDetailQueryMock = vi.fn()

function buildSignalDetail(overrides: Record<string, unknown> = {}) {
  return {
    id: 'sig-1',
    title: 'Fuite d eau',
    location_text: 'Cuisine',
    status: 'open',
    responsible_business_unit_key: 'rooftop',
    responsible_business_unit_label: 'Rooftop',
    permission_hints: {
      can_create_linked_action_plan: true,
    },
    ...overrides,
  }
}

const { mockAuthState, mockBusinessUnitTree } = vi.hoisted(() => ({
  mockBusinessUnitTree: {
    business_units: [{ id: 'bu-1', label: 'Rooftop', key: 'rooftop', unit_type: 'service' }],
  },
  mockAuthState: {
    bootstrap: {
      active_membership: {
        id: 'member-manager',
        establishment_id: 'est-1',
        role: 'manager',
        scopes: [],
      },
      user: {
        id: 'user-manager',
        username: 'manager_user',
      },
      permission_hints: {
        chat_available: false,
        can_create_action_plan: true,
        can_create_catalog_action_plan: true,
        can_view_action_plan_catalog: true,
        can_invite: false,
        can_manage_runtime_config: false,
      },
    },
    activeMembership: {
      id: 'member-manager',
      establishment_id: 'est-1',
      role: 'manager',
      scopes: [],
    },
  },
}))

vi.mock('@/app/app-routes', () => ({
  useAppRoute: () => ({ navigate }),
}))

vi.mock('@/app/auth-provider', () => ({
  useAuth: () => mockAuthState,
}))

vi.mock('@/features/auth/hooks', () => ({
  useBusinessUnitTreeQuery: () => ({
    data: mockBusinessUnitTree,
    isLoading: false,
    isError: false,
  }),
}))

vi.mock('../hooks', () => ({
  useCreateActionPlanMutation: () => ({
    mutateAsync: createMutateAsync,
    isPending: false,
  }),
  useUpdateActionPlanMutation: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
  useActionPlanDetailQuery: () => ({
    isLoading: false,
    isError: false,
    data: null,
    refetch: vi.fn(),
  }),
}))

vi.mock('../components/action-plan-event-planning-form', () => ({
  ActionPlanEventPlanningForm: ({
    draft,
    onDraftChange,
  }: {
    draft: { assignees: Array<Record<string, string>> }
    onDraftChange: (draft: Record<string, unknown>) => void
  }) => {
    useEffect(() => {
      if (draft.assignees.length > 0) {
        return
      }
      onDraftChange({
        ...draft,
        assignees: [
          {
            id: 'a1',
            membershipId: 'member-1',
            businessUnitId: 'bu-1',
            displayName: 'Marie Dupont',
            startAt: '',
            endAt: '',
            visibleFrom: '',
          },
        ],
      })
    }, [draft, onDraftChange])
    return createElement('div', { 'data-testid': 'event-planning-form' })
  },
}))

vi.mock('@/features/signals/hooks', () => ({
  useSignalDetailQuery: () => signalDetailQueryMock(),
}))

vi.mock('@/features/signals/components/signal-classification-badges', () => ({
  SignalClassificationBadges: () => null,
}))

vi.mock('@/features/action-plans/components/action-linked-signal-strip', () => ({
  ActionLinkedSignalStrip: ({ children }: { children: unknown }) => children,
}))

vi.mock('@/features/action-plans/components/action-linked-signal-card', () => ({
  ActionLinkedSignalCard: ({ title }: { title: string }) =>
    createElement('div', { 'data-testid': 'linked-signal-card' }, title),
}))

function addTask() {
  fireEvent.click(screen.getByRole('button', { name: 'Ajouter une tâche' }))
}

function selectTaskBusinessUnit(taskIndex: number, label: string) {
  const advancedButtons = screen.getAllByRole('button', { name: 'Options avancées' })
  fireEvent.click(advancedButtons[taskIndex]!)
  const poleButtons = screen.getAllByRole('button', { name: "Pôle d'activité" })
  fireEvent.click(poleButtons[taskIndex]!)
  const optionButtons = screen.getAllByRole('button', { name: label })
  fireEvent.click(optionButtons[optionButtons.length - 1]!)
}

function renderPage(
  props: {
    mode?: 'catalog' | 'execution' | 'signal-linked'
    backPath?: string
    signalId?: string
  } = {},
) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })

  return render(
    createElement(
      QueryClientProvider,
      { client: queryClient },
      createElement(ActionPlanCreatePage, props),
    ),
  )
}

describe('ActionPlanCreatePage', () => {
  beforeEach(() => {
    navigate.mockReset()
    createMutateAsync.mockReset()
    signalDetailQueryMock.mockReset()
    signalDetailQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: buildSignalDetail(),
      refetch: vi.fn(),
    })
    createMutateAsync.mockResolvedValue({
      id: 'exec-1',
      object_type: 'action_plan_execution',
      status: 'in_progress',
      action_plan_id: 'plan-1',
    })

    mockAuthState.bootstrap.active_membership = {
      id: 'member-manager',
      establishment_id: 'est-1',
      role: 'manager',
      scopes: [],
    }
    mockAuthState.bootstrap.user = {
      id: 'user-manager',
      username: 'manager_user',
    }
    mockAuthState.bootstrap.permission_hints = {
      chat_available: false,
      can_create_action_plan: true,
      can_create_catalog_action_plan: true,
      can_view_action_plan_catalog: true,
      can_invite: false,
      can_manage_runtime_config: false,
    }
    mockAuthState.activeMembership = {
      id: 'member-manager',
      establishment_id: 'est-1',
      role: 'manager',
      scopes: [],
    }
    mockBusinessUnitTree.business_units = [
      { id: 'bu-1', label: 'Rooftop', key: 'rooftop', unit_type: 'service' },
    ]
  })

  afterEach(() => {
    cleanup()
  })

  it('aligns library switch label with validation switch label', () => {
    mockAuthState.bootstrap.active_membership = {
      id: 'member-owner',
      establishment_id: 'est-1',
      role: 'owner',
      scopes: [],
    }
    mockAuthState.activeMembership = {
      id: 'member-owner',
      establishment_id: 'est-1',
      role: 'owner',
      scopes: [],
    }

    renderPage({ mode: 'catalog' })

    const validationLabel = screen.getByText('Validation requise')
    const libraryLabel = screen.getByText('Enregistrer dans la bibliothèque')

    expect(validationLabel.getBoundingClientRect().left).toBe(libraryLabel.getBoundingClientRect().left)
  })

  it('selects pilot pole via pill wheel and submits with pilot_business_unit_id', async () => {
    mockBusinessUnitTree.business_units = [
      { id: 'bu-restaurant', label: 'Restaurant', key: 'restaurant', unit_type: 'service' },
      { id: 'bu-maintenance', label: 'Maintenance', key: 'maintenance', unit_type: 'service' },
    ]

    renderPage({ mode: 'catalog' })

    fireEvent.click(screen.getByRole('button', { name: "Pôle d'activité pilote" }))
    fireEvent.click(screen.getByRole('button', { name: 'Maintenance' }))

    fireEvent.change(screen.getAllByRole('textbox')[0], { target: { value: 'Plan maintenance pilote' } })
    addTask()
    fireEvent.change(screen.getByLabelText('Titre de la tâche'), { target: { value: 'Tâche 1' } })
    selectTaskBusinessUnit(0, 'Maintenance')
    fireEvent.click(screen.getByRole('switch', { name: 'Enregistrer dans la bibliothèque' }))
    fireEvent.click(screen.getByRole('button', { name: 'Enregistrer dans la bibliothèque' }))

    await waitFor(() => {
      expect(createMutateAsync).toHaveBeenCalledWith(
        expect.objectContaining({
          title: 'Plan maintenance pilote',
          pilot_business_unit_id: 'bu-maintenance',
        }),
      )
    })
  })

  it('keeps selected pilot pole when reopening the picker', () => {
    mockBusinessUnitTree.business_units = [
      { id: 'bu-comm', label: 'Communication', key: 'communication', unit_type: 'service' },
      { id: 'bu-coworking', label: 'Coworking', key: 'coworking', unit_type: 'service' },
    ]

    renderPage({ mode: 'catalog' })

    const pilotPill = screen.getByRole('button', { name: "Pôle d'activité pilote" })
    fireEvent.click(pilotPill)
    fireEvent.click(screen.getByRole('button', { name: 'Coworking' }))
    expect(screen.getByRole('button', { name: "Pôle d'activité pilote" })).toHaveProperty(
      'textContent',
      'Coworking',
    )

    fireEvent.click(screen.getByRole('button', { name: "Pôle d'activité pilote", pressed: true }))
    fireEvent.click(screen.getByRole('button', { name: "Pôle d'activité pilote" }))

    expect(screen.getByRole('button', { name: "Pôle d'activité pilote" })).toHaveProperty(
      'textContent',
      'Coworking',
    )
  })

  it('submits owner catalog create with multi-pole tasks when pilot pole is not explicitly selected', async () => {
    mockAuthState.bootstrap.active_membership = {
      id: 'member-owner',
      establishment_id: 'est-1',
      role: 'owner',
      scopes: [],
    }
    mockAuthState.activeMembership = {
      id: 'member-owner',
      establishment_id: 'est-1',
      role: 'owner',
      scopes: [],
    }
    mockBusinessUnitTree.business_units = [
      { id: 'bu-restaurant', label: 'Restaurant', key: 'restaurant', unit_type: 'service' },
      { id: 'bu-maintenance', label: 'Maintenance', key: 'maintenance', unit_type: 'service' },
    ]

    renderPage({ mode: 'catalog' })

    fireEvent.change(screen.getAllByRole('textbox')[0], { target: { value: 'Plan multi-pôles' } })
    addTask()
    fireEvent.change(screen.getByLabelText('Titre de la tâche'), { target: { value: 'Tâche restaurant' } })
    selectTaskBusinessUnit(0, 'Restaurant')
    fireEvent.click(screen.getByRole('button', { name: 'Ajouter une tâche' }))

    const taskInputs = screen.getAllByLabelText('Titre de la tâche')
    fireEvent.change(taskInputs[1], { target: { value: 'Tâche maintenance' } })

    const advancedButtons = screen.getAllByRole('button', { name: 'Options avancées' })
    fireEvent.click(advancedButtons[1]!)
    const poleButtons = screen.getAllByRole('button', { name: "Pôle d'activité" })
    fireEvent.click(poleButtons[1]!)
    const maintenanceOptions = screen.getAllByRole('button', { name: 'Maintenance' })
    fireEvent.click(maintenanceOptions[maintenanceOptions.length - 1]!)

    fireEvent.click(screen.getByRole('switch', { name: 'Enregistrer dans la bibliothèque' }))
    fireEvent.click(screen.getByRole('button', { name: 'Enregistrer dans la bibliothèque' }))

    await waitFor(() => {
      expect(createMutateAsync).toHaveBeenCalledWith(
        expect.objectContaining({
          title: 'Plan multi-pôles',
          pilot_business_unit_id: 'bu-restaurant',
          is_reusable: true,
          assignees: [],
          tasks: [
            expect.objectContaining({
              task: 'Tâche restaurant',
              business_unit_id: 'bu-restaurant',
              position: 1,
            }),
            expect.objectContaining({
              task: 'Tâche maintenance',
              business_unit_id: 'bu-maintenance',
              position: 2,
            }),
          ],
        }),
      )
    })
  })

  it('submits catalog create with is_reusable true when save to library is enabled', async () => {
    renderPage({ mode: 'catalog' })

    const textInputs = screen.getAllByRole('textbox')
    fireEvent.change(textInputs[0], { target: { value: 'Plan catalogue' } })
    addTask()
    fireEvent.change(screen.getByLabelText('Titre de la tâche'), { target: { value: 'Task 1' } })
    selectTaskBusinessUnit(0, 'Rooftop')
    fireEvent.click(screen.getByRole('switch', { name: 'Enregistrer dans la bibliothèque' }))
    fireEvent.click(screen.getByRole('button', { name: 'Enregistrer dans la bibliothèque' }))

    await waitFor(() => {
      expect(createMutateAsync).toHaveBeenCalledWith(
        expect.objectContaining({
          title: 'Plan catalogue',
          is_reusable: true,
          assignees: [],
        }),
      )
    })
  })

  it('submits catalog create without tasks when save to library is enabled', async () => {
    renderPage({ mode: 'catalog' })

    fireEvent.change(screen.getAllByRole('textbox')[0], { target: { value: 'Plan catalogue vide' } })
    fireEvent.click(screen.getByRole('switch', { name: 'Enregistrer dans la bibliothèque' }))
    fireEvent.click(screen.getByRole('button', { name: 'Enregistrer dans la bibliothèque' }))

    await waitFor(() => {
      expect(createMutateAsync).toHaveBeenCalledWith(
        expect.objectContaining({
          title: 'Plan catalogue vide',
          is_reusable: true,
          assignees: [],
          tasks: [],
        }),
      )
    })
  })

  it('submits execution staff create with locked payload and skips submit when title is empty', async () => {
    mockAuthState.bootstrap.active_membership = {
      id: 'staff-member-1',
      establishment_id: 'est-1',
      role: 'staff',
      scopes: [{ scope_type: 'business_unit', scope_id: 'bu-1' }],
    }
    mockAuthState.bootstrap.user = {
      id: 'user-staff',
      username: 'staff_user',
    }
    mockAuthState.activeMembership = {
      id: 'staff-member-1',
      establishment_id: 'est-1',
      role: 'staff',
      scopes: [{ scope_type: 'business_unit', scope_id: 'bu-1' }],
    }

    renderPage({ mode: 'execution', backPath: '/execution' })

    fireEvent.click(screen.getByRole('button', { name: 'Créer le plan d’action' }))
    expect(createMutateAsync).not.toHaveBeenCalled()

    const titleInput = screen.getAllByRole('textbox')[0]
    fireEvent.change(titleInput, { target: { value: 'Plan staff' } })
    addTask()
    fireEvent.change(screen.getByLabelText('Titre de la tâche'), { target: { value: 'Tâche 1' } })
    selectTaskBusinessUnit(0, 'Rooftop')

    fireEvent.click(screen.getByRole('button', { name: 'Créer le plan d’action' }))

    await waitFor(() => {
      expect(createMutateAsync).toHaveBeenCalledWith(
        expect.objectContaining({
          title: 'Plan staff',
          requires_validation: false,
          is_reusable: false,
          assignees: [
            expect.objectContaining({
              membership_id: 'staff-member-1',
              business_unit_id: 'bu-1',
            }),
          ],
        }),
      )
    })
  })

  it('locks pilot pole and submits signal-linked create with coherent pilot_business_unit_id', async () => {
    renderPage({
      mode: 'signal-linked',
      signalId: 'sig-1',
      backPath: '/signals/sig-1',
    })

    expect(screen.queryByRole('button', { name: "Pôle d'activité pilote" })).toBeNull()
    expect(screen.getAllByText('Rooftop').length).toBeGreaterThanOrEqual(1)

    const titleInput = screen.getAllByRole('textbox')[0]
    fireEvent.change(titleInput, { target: { value: 'Plan signal' } })
    addTask()
    fireEvent.change(screen.getByLabelText('Titre de la tâche'), { target: { value: 'Tâche signal' } })
    selectTaskBusinessUnit(0, 'Rooftop')
    fireEvent.click(screen.getByRole('button', { name: 'Créer le plan d’action' }))

    await waitFor(() => {
      expect(createMutateAsync).toHaveBeenCalledWith(
        expect.objectContaining({
          title: 'Plan signal',
          source_signal_id: 'sig-1',
          pilot_business_unit_id: 'bu-1',
        }),
      )
    })
    expect(navigate).toHaveBeenCalledWith('/action-plans/executions/exec-1')
  })

  it('blocks signal-linked create for staff before showing the form', () => {
    mockAuthState.bootstrap.active_membership = {
      id: 'staff-member-1',
      establishment_id: 'est-1',
      role: 'staff',
      scopes: [{ scope_type: 'business_unit', scope_id: 'bu-1' }],
    }
    mockAuthState.activeMembership = {
      id: 'staff-member-1',
      establishment_id: 'est-1',
      role: 'staff',
      scopes: [{ scope_type: 'business_unit', scope_id: 'bu-1' }],
    }

    renderPage({
      mode: 'signal-linked',
      signalId: 'sig-1',
      backPath: '/signals/sig-1',
    })

    expect(
      screen.getByText("Vous n'avez pas la permission de créer un plan d'action."),
    ).toBeTruthy()
    expect(createMutateAsync).not.toHaveBeenCalled()
  })

  it('blocks signal-linked create when signal hint denies access', () => {
    signalDetailQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: buildSignalDetail({
        permission_hints: { can_create_linked_action_plan: false },
      }),
      refetch: vi.fn(),
    })

    renderPage({
      mode: 'signal-linked',
      signalId: 'sig-1',
      backPath: '/signals/sig-1',
    })

    expect(
      screen.getByText("Vous n'avez pas la permission de créer un plan d'action."),
    ).toBeTruthy()
    expect(createMutateAsync).not.toHaveBeenCalled()
  })
})
