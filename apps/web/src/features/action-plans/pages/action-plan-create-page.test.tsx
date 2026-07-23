// @vitest-environment jsdom

import { createElement, useEffect } from 'react'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { notifySuccess } from '@/lib/success-toast'

import { ActionPlanCreatePage } from './action-plan-create-page'

vi.mock('@/lib/success-toast', async () => {
  const actual = await vi.importActual<typeof import('@/lib/success-toast')>('@/lib/success-toast')
  return {
    ...actual,
    notifySuccess: vi.fn(),
  }
})

const navigate = vi.fn()
const createMutateAsync = vi.fn()
const scheduleMutateAsync = vi.fn()
const useMutateAsync = vi.fn()
const planningMutateAsync = vi.fn()
const signalDetailQueryMock = vi.fn()
const detailQueryMock = vi.fn()

function buildTemplatePlan(overrides: Record<string, unknown> = {}) {
  return {
    id: 'plan-1',
    title: 'Plan catalogue',
    description: 'Description',
    catalog_status: 'active',
    pilot_business_unit: { id: 'bu-1', specific_name: 'Rooftop', instance_description: '', active: true, generic: { key: 'rooftop', label: 'Rooftop', description: '', unit_type: 'dedicated' } },
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
        business_unit: { id: 'bu-1', specific_name: 'Rooftop', instance_description: '', active: true, generic: { key: 'rooftop', label: 'Rooftop', description: '', unit_type: 'dedicated' } },
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

function buildSignalDetail(overrides: Record<string, unknown> = {}) {
  return {
    id: 'sig-1',
    title: 'Fuite d eau',
    location_text: 'Cuisine',
    status: 'open',
    responsible_business_unit_id: 'bu-1',
    responsible_business_unit_key: 'rooftop',
    responsible_business_unit_label: 'Rooftop',
    affected_business_unit_id: null,
    activity_subject_id: null,
    permission_hints: {
      can_create_linked_action_plan: true,
    },
    ...overrides,
  }
}

const { mockAuthState, mockBusinessUnitTree, perAssigneeTestMode } = vi.hoisted(() => ({
  mockBusinessUnitTree: {
    business_units: [{
      id: 'bu-1',
      specific_name: 'Rooftop',
      instance_description: '',
      active: true,
      generic: { key: 'rooftop', label: 'Rooftop', description: '', unit_type: 'dedicated' },
      activity_subjects: [],
    }],
  },
  perAssigneeTestMode: { enabled: false, incomplete: false },
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

vi.mock('../lib/action-plan-planning-submission-intent', async (importOriginal) => {
  const actual =
    await importOriginal<typeof import('../lib/action-plan-planning-submission-intent')>()
  return {
    ...actual,
    resolvePlanningSubmissionIntent: vi.fn(
      async (options: { body: { items: unknown[] } }) => ({
        submissionId: 'sub-create',
        requestHash: 'hash',
        itemIds: options.body.items.map((_, index) => `item-create-${index}`),
      }),
    ),
    clearPlanningSubmissionIntent: vi.fn(),
  }
})

vi.mock('../hooks', () => ({
  useCreateActionPlanMutation: () => ({
    mutateAsync: createMutateAsync,
    isPending: false,
  }),
  useSubmitActionPlanPlanningMutation: () => ({
    mutateAsync: planningMutateAsync,
    isPending: false,
  }),
  useUpdateActionPlanMutation: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
  useActionPlanDetailQuery: () => detailQueryMock(),
  useScheduleActionPlanFromCatalogMutation: () => ({
    mutateAsync: scheduleMutateAsync,
    isPending: false,
  }),
  useUseActionPlanFromCatalogMutation: () => ({
    mutateAsync: useMutateAsync,
    isPending: false,
  }),
}))

vi.mock('../components/action-plan-event-planning-form', () => ({
  ActionPlanEventPlanningForm: ({
    draft,
    onDraftChange,
  }: {
    draft: Record<string, unknown> & { assignees: Array<Record<string, unknown>> }
    onDraftChange: (draft: Record<string, unknown>) => void
  }) => {
    useEffect(() => {
      if (perAssigneeTestMode.enabled) {
        if (draft.usePerAssigneeChronology) {
          return
        }
        onDraftChange({
          ...draft,
          usePerAssigneeChronology: true,
          assignees: [
            {
              id: 'a-recurring',
              membershipId: 'member-1',
              businessUnitId: 'bu-1',
              displayName: 'Luffy',
              startAt: '2026-07-12T03:00:00.000Z',
              endAt: '2026-07-12T14:05:00.000Z',
              visibleFrom: '',
              repeatEnabled: true,
              recurrenceDays: perAssigneeTestMode.incomplete ? [] : ['tuesday', 'thursday', 'saturday'],
              recurrenceEndDate: perAssigneeTestMode.incomplete ? '' : '2026-07-25',
            },
            {
              id: 'a-one-shot',
              membershipId: 'member-2',
              businessUnitId: 'bu-1',
              displayName: 'Nami',
              startAt: perAssigneeTestMode.incomplete ? '' : '2026-07-11T03:00:00.000Z',
              endAt: perAssigneeTestMode.incomplete ? '' : '2026-07-25T06:00:00.000Z',
              visibleFrom: '',
              repeatEnabled: false,
              recurrenceDays: [],
              recurrenceEndDate: '',
            },
          ],
        })
        return
      }

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
            repeatEnabled: false,
            recurrenceDays: [],
            recurrenceEndDate: '',
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
    mode?: 'catalog' | 'execution' | 'signal-linked' | 'template-edit'
    backPath?: string
    signalId?: string
    actionPlanId?: string
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
    scheduleMutateAsync.mockReset()
    useMutateAsync.mockReset()
    detailQueryMock.mockReset()
    detailQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: null,
      refetch: vi.fn(),
    })
    perAssigneeTestMode.enabled = false
    perAssigneeTestMode.incomplete = false
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
    scheduleMutateAsync.mockResolvedValue({ id: 'schedule-1' })
    useMutateAsync.mockResolvedValue({ id: 'exec-2' })

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
      {
      id: 'bu-1',
      specific_name: 'Rooftop',
      instance_description: '',
      active: true,
      generic: { key: 'rooftop', label: 'Rooftop', description: '', unit_type: 'dedicated' },
      activity_subjects: [],
    },
    ]
  })

  afterEach(() => {
    cleanup()
  })

  it('renders Options section before tasks', () => {
    renderPage({ mode: 'catalog' })

    const optionsLabel = screen.getByText('Options')
    const addTaskButton = screen.getByRole('button', { name: 'Ajouter une tâche' })

    expect(
      optionsLabel.compareDocumentPosition(addTaskButton) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy()
  })

  it('keeps planning form visible when save to library is enabled', () => {
    renderPage({ mode: 'catalog' })
    fireEvent.click(screen.getByRole('switch', { name: 'Enregistrer dans la bibliothèque' }))
    expect(screen.getByTestId('event-planning-form')).toBeTruthy()
  })

  it('always uses library submit label when save to library is enabled', () => {
    renderPage({ mode: 'catalog' })

    fireEvent.change(screen.getAllByRole('textbox')[0], { target: { value: 'Plan catalogue' } })
    fireEvent.click(screen.getByRole('switch', { name: 'Enregistrer dans la bibliothèque' }))

    expect(screen.queryByRole('button', { name: 'Enregistrer et planifier' })).toBeNull()
    expect(screen.getByRole('button', { name: 'Enregistrer dans la bibliothèque' })).toBeTruthy()
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
      {
      id: 'bu-restaurant',
      specific_name: 'Restaurant',
      instance_description: '',
      active: true,
      generic: { key: 'restaurant', label: 'Restaurant', description: '', unit_type: 'dedicated' },
      activity_subjects: [],
    },
      {
      id: 'bu-maintenance',
      specific_name: 'Maintenance',
      instance_description: '',
      active: true,
      generic: { key: 'maintenance', label: 'Maintenance', description: '', unit_type: 'dedicated' },
      activity_subjects: [],
    },
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
      {
      id: 'bu-comm',
      specific_name: 'Communication',
      instance_description: '',
      active: true,
      generic: { key: 'communication', label: 'Communication', description: '', unit_type: 'dedicated' },
      activity_subjects: [],
    },
      {
      id: 'bu-coworking',
      specific_name: 'Coworking',
      instance_description: '',
      active: true,
      generic: { key: 'coworking', label: 'Coworking', description: '', unit_type: 'dedicated' },
      activity_subjects: [],
    },
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
      {
      id: 'bu-restaurant',
      specific_name: 'Restaurant',
      instance_description: '',
      active: true,
      generic: { key: 'restaurant', label: 'Restaurant', description: '', unit_type: 'dedicated' },
      activity_subjects: [],
    },
      {
      id: 'bu-maintenance',
      specific_name: 'Maintenance',
      instance_description: '',
      active: true,
      generic: { key: 'maintenance', label: 'Maintenance', description: '', unit_type: 'dedicated' },
      activity_subjects: [],
    },
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
    expect(navigate).toHaveBeenCalledWith('/execution')
  })

  it('resolves locked pilot from responsible_business_unit_id without matching generic.key', async () => {
    signalDetailQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: buildSignalDetail({
        responsible_business_unit_id: 'bu-food-court',
        responsible_business_unit_key: 'food_court',
        responsible_business_unit_label: 'Food Court',
      }),
    })
    mockBusinessUnitTree.business_units = [
      {
        id: 'bu-food-court',
        specific_name: 'Food Court',
        instance_description: '',
        active: true,
        generic: {
          key: 'restaurant',
          label: 'Restaurant',
          description: '',
          unit_type: 'dedicated',
        },
        activity_subjects: [],
      },
      {
        id: 'bu-rooftop',
        specific_name: 'Rooftop',
        instance_description: '',
        active: true,
        generic: {
          key: 'restaurant',
          label: 'Restaurant',
          description: '',
          unit_type: 'dedicated',
        },
        activity_subjects: [],
      },
    ]

    renderPage({
      mode: 'signal-linked',
      signalId: 'sig-1',
      backPath: '/signals/sig-1',
    })

    const titleInput = screen.getAllByRole('textbox')[0]
    fireEvent.change(titleInput, { target: { value: 'Plan Food Court' } })
    addTask()
    fireEvent.change(screen.getByLabelText('Titre de la tâche'), {
      target: { value: 'Tâche Food Court' },
    })
    selectTaskBusinessUnit(0, 'Food Court')
    fireEvent.click(screen.getByRole('button', { name: 'Créer le plan d’action' }))

    await waitFor(() => {
      expect(createMutateAsync).toHaveBeenCalledWith(
        expect.objectContaining({
          pilot_business_unit_id: 'bu-food-court',
          source_signal_id: 'sig-1',
        }),
      )
    })
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

  it('creates per-assignee plan via single atomic create with planning intent', async () => {
    perAssigneeTestMode.enabled = true
    createMutateAsync.mockResolvedValue({
      replayed: false,
      action_plan_id: 'plan-per-assignee-1',
      summary: { executions_created: 1, schedules_created: 1 },
      executions: [],
      schedules: [],
    })

    renderPage({ mode: 'catalog' })

    fireEvent.change(screen.getAllByRole('textbox')[0], { target: { value: 'Plan per-assigné' } })
    addTask()
    fireEvent.change(screen.getByLabelText('Titre de la tâche'), { target: { value: 'Tâche 1' } })
    selectTaskBusinessUnit(0, 'Rooftop')

    expect(screen.queryByRole('button', { name: 'Planifier la récurrence' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Lancer pour cet assigné' })).toBeNull()

    fireEvent.click(screen.getByRole('button', { name: 'Créer le plan d’action' }))

    await waitFor(() => {
      expect(createMutateAsync).toHaveBeenCalledTimes(1)
      expect(planningMutateAsync).not.toHaveBeenCalled()
      expect(scheduleMutateAsync).not.toHaveBeenCalled()
      expect(useMutateAsync).not.toHaveBeenCalled()
      expect(navigate).toHaveBeenCalledWith('/execution')
    })

    const createBody = createMutateAsync.mock.calls[0][0]
    expect(createBody.is_reusable).toBe(false)
    expect(createBody.submission_id).toBe('sub-create')
    expect(createBody.use_shared_chronology).toBe(false)
    expect(createBody.items).toHaveLength(2)
    expect(notifySuccess).toHaveBeenCalledWith({
      message: '1 planification et 1 exécution créées.',
      kind: 'created',
    })
  })

  it('blocks per-assignee create when assignee cards are incomplete', async () => {
    perAssigneeTestMode.enabled = true
    perAssigneeTestMode.incomplete = true

    renderPage({ mode: 'catalog' })

    fireEvent.change(screen.getAllByRole('textbox')[0], { target: { value: 'Plan incomplet' } })
    addTask()
    fireEvent.change(screen.getByLabelText('Titre de la tâche'), { target: { value: 'Tâche 1' } })
    selectTaskBusinessUnit(0, 'Rooftop')

    fireEvent.click(screen.getByRole('button', { name: 'Créer le plan d’action' }))

    await waitFor(() => {
      expect(createMutateAsync).not.toHaveBeenCalled()
      expect(scheduleMutateAsync).not.toHaveBeenCalled()
      expect(useMutateAsync).not.toHaveBeenCalled()
    })
  })

  it('renders template edit save button with brand color', async () => {
    detailQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: buildTemplatePlan(),
      refetch: vi.fn(),
    })

    renderPage({ mode: 'template-edit', actionPlanId: 'plan-1' })

    const saveButton = await screen.findByRole('button', { name: 'Enregistrer les modifications' })
    expect(saveButton.className).toContain('bg-[#114660]')
  })
})
