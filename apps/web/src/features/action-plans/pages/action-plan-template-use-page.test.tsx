// @vitest-environment jsdom

import { createElement, type ReactNode } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { ActionPlanDetail } from '@/features/action-plans/types'

import { ActionPlanTemplateUsePage } from './action-plan-template-use-page'

const keyboardOpen = vi.hoisted(() => ({ current: false }))
const detailQueryMock = vi.fn()
const navigateMock = vi.fn()
const planningMutationMock = vi.fn()

vi.mock('@/lib/native-keyboard', () => ({
  useNativeKeyboardOpen: () => keyboardOpen.current,
}))

vi.mock('@/lib/success-toast', () => ({
  notifySuccess: vi.fn(),
}))

function buildPlan(overrides: Partial<ActionPlanDetail> = {}): ActionPlanDetail {
  return {
    id: 'plan-1',
    title: 'Plan catalogue',
    description: 'Description',
    catalog_status: 'active',
    pilot_business_unit: {
      id: 'bu-1',
      specific_name: 'Restaurant',
      instance_description: '',
      active: true,
      generic: { key: 'restaurant', label: 'Restaurant', description: '', unit_type: 'dedicated' },
    },
    task_count: 2,
    involved_pole_count: 1,
    created_at: '2026-06-30T08:00:00Z',
    updated_at: '2026-06-30T10:00:00Z',
    created_by_id: 'member-1',
    created_by_display_name: 'Alice',
    requires_validation: true,
    is_reusable: true,
    tasks: [],
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

function selectCurrentUser() {
  fireEvent.click(screen.getByRole('button', { name: /Assignés/ }))
  fireEvent.click(screen.getByRole('button', { name: 'Moi' }))
  fireEvent.click(screen.getByRole('button', { name: 'Valider' }))
}

function renderPage(ui: ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(createElement(QueryClientProvider, { client: queryClient }, ui))
}

function enableDesktopWeb() {
  vi.stubEnv('VITE_APP_RUNTIME', 'web')
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
}

vi.mock('@/app/app-routes', () => ({
  useAppRoute: () => ({
    navigate: navigateMock,
    route: { kind: 'action-plan-template-use', actionPlanId: 'plan-1' },
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
    resolvePlanningSubmissionIntent: vi.fn(async (options: { body: { items: unknown[] } }) => ({
      submissionId: 'sub-fixed',
      requestHash: 'hash',
      itemIds: options.body.items.map((_, index) => `item-fixed-${index}`),
    })),
    clearPlanningSubmissionIntent: vi.fn(),
  }
})

vi.mock('@/features/users/hooks', () => ({
  useEstablishmentUserSearchQuery: () => ({
    data: [
      {
        id: 'membership-1',
        membership_id: 'membership-1',
        display_name: 'Camille',
        username: 'camille',
        role: 'manager',
        email: null,
        business_unit_ids: ['bu-1'],
      },
    ],
    isFetching: false,
  }),
}))

vi.mock('../hooks', () => ({
  useActionPlanDetailQuery: () => detailQueryMock(),
  useSubmitActionPlanPlanningMutation: () => planningMutationMock(),
}))

describe('ActionPlanTemplateUsePage', () => {
  beforeEach(() => {
    keyboardOpen.current = false
    detailQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: buildPlan(),
      refetch: vi.fn(),
    })
    planningMutationMock.mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    })
  })

  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
    vi.unstubAllEnvs()
    Reflect.deleteProperty(window, 'matchMedia')
  })

  it('replaces a desktop web deep link with the template detail', () => {
    enableDesktopWeb()

    renderPage(createElement(ActionPlanTemplateUsePage, { actionPlanId: 'plan-1' }))

    expect(navigateMock).toHaveBeenCalledWith('/action-plans/plan-1', { replace: true })
    expect(screen.queryByRole('button', { name: 'Lancer le plan' })).toBeNull()
  })

  it('keeps the launch page on a large native viewport', () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
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

    renderPage(createElement(ActionPlanTemplateUsePage, { actionPlanId: 'plan-1' }))

    expect(screen.getByRole('heading', { name: 'Plan catalogue' })).toBeTruthy()
    expect(screen.getByText(/2 tâches/)).toBeTruthy()
    expect(screen.getByText(/Restaurant/)).toBeTruthy()
    expect(screen.getByText('Validation requise')).toBeTruthy()
    expect(
      (screen.getByRole('button', { name: 'Lancer le plan' }) as HTMLButtonElement).disabled,
    ).toBe(true)
    expect(navigateMock).not.toHaveBeenCalled()
  })

  it('submits an empty draft for Maintenant', async () => {
    const mutateAsync = vi.fn().mockResolvedValue({
      replayed: false,
      summary: { executions_created: 1, schedules_created: 0 },
      executions: [{ item_id: 'i1', id: 'exec-1', primary_membership_id: null, status: 'in_progress' }],
      schedules: [],
    })
    planningMutationMock.mockReturnValue({ mutateAsync, isPending: false })

    renderPage(createElement(ActionPlanTemplateUsePage, { actionPlanId: 'plan-1' }))
    expect(
      (screen.getByRole('button', { name: 'Lancer le plan' }) as HTMLButtonElement).disabled,
    ).toBe(true)
    selectCurrentUser()
    fireEvent.click(screen.getByRole('switch', { name: 'Validation requise' }))
    fireEvent.click(screen.getByRole('button', { name: 'Lancer le plan' }))

    await vi.waitFor(() => {
      expect(mutateAsync).toHaveBeenCalled()
    })
    const body = mutateAsync.mock.calls[0]?.[0].body
    expect(body.use_shared_chronology).toBe(true)
    expect(body.requires_validation).toBe(false)
    expect(body.items[0]).toMatchObject({
      kind: 'execution',
      start_at: null,
      end_at: null,
      assignees: [
        expect.objectContaining({
          membership_id: 'membership-1',
          business_unit_id: 'bu-1',
        }),
      ],
    })
    expect(navigateMock).toHaveBeenCalledWith('/action-plans/executions/exec-1')
  })

  it('reveals schedule fields and hides recurrence without permission', () => {
    renderPage(createElement(ActionPlanTemplateUsePage, { actionPlanId: 'plan-1' }))

    expect(screen.queryByText('Répéter')).toBeNull()
    fireEvent.click(screen.getByRole('tab', { name: 'Planifier' }))
    expect(screen.getByText('Début')).toBeTruthy()
    expect(screen.getByText('Journée entière')).toBeTruthy()
    expect(screen.getByText('Répéter')).toBeTruthy()

    detailQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: buildPlan({
        permission_hints: {
          can_update: false,
          can_activate: false,
          can_deactivate: false,
          can_delete: false,
          can_use: true,
          can_schedule: false,
        },
      }),
      refetch: vi.fn(),
    })
    cleanup()
    renderPage(createElement(ActionPlanTemplateUsePage, { actionPlanId: 'plan-1' }))
    fireEvent.click(screen.getByRole('tab', { name: 'Planifier' }))
    expect(screen.queryByText('Répéter')).toBeNull()
  })

  it('returns to an empty Maintenant draft after scheduling fields', async () => {
    const mutateAsync = vi.fn().mockResolvedValue({
      replayed: false,
      summary: { executions_created: 1, schedules_created: 0 },
      executions: [{ item_id: 'i1', id: 'exec-2', primary_membership_id: null, status: 'in_progress' }],
      schedules: [],
    })
    planningMutationMock.mockReturnValue({ mutateAsync, isPending: false })

    renderPage(createElement(ActionPlanTemplateUsePage, { actionPlanId: 'plan-1' }))
    fireEvent.click(screen.getByRole('tab', { name: 'Planifier' }))
    fireEvent.click(screen.getByRole('switch', { name: 'Répéter' }))
    fireEvent.click(screen.getByRole('tab', { name: 'Maintenant' }))
    selectCurrentUser()
    fireEvent.click(screen.getByRole('button', { name: 'Lancer le plan' }))

    await vi.waitFor(() => {
      expect(mutateAsync).toHaveBeenCalled()
    })
    expect(mutateAsync.mock.calls[0]?.[0].body.items[0]).toMatchObject({
      kind: 'execution',
      start_at: null,
      end_at: null,
    })
  })

  it('disables the launch action while the mutation is pending', () => {
    planningMutationMock.mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: true,
    })

    renderPage(createElement(ActionPlanTemplateUsePage, { actionPlanId: 'plan-1' }))

    expect(screen.getByRole('button', { name: 'Lancer le plan' })).toHaveProperty('disabled', true)
  })

  it('stays on the execution feed when the launch creates a schedule', async () => {
    const mutateAsync = vi.fn().mockResolvedValue({
      replayed: false,
      summary: { executions_created: 0, schedules_created: 1 },
      executions: [],
      schedules: [{ item_id: 'i1', id: 'sched-1', primary_membership_id: null, status: 'active' }],
    })
    planningMutationMock.mockReturnValue({ mutateAsync, isPending: false })

    renderPage(createElement(ActionPlanTemplateUsePage, { actionPlanId: 'plan-1' }))
    selectCurrentUser()
    fireEvent.click(screen.getByRole('button', { name: 'Lancer le plan' }))

    await vi.waitFor(() => {
      expect(navigateMock).toHaveBeenCalledWith('/execution')
    })
  })

  it('hides the launch action while the native keyboard is open', () => {
    keyboardOpen.current = true

    renderPage(createElement(ActionPlanTemplateUsePage, { actionPlanId: 'plan-1' }))

    expect(screen.queryByRole('button', { name: 'Lancer le plan' })).toBeNull()
  })

  it('keeps per-assignee chronology behind advanced options', () => {
    renderPage(createElement(ActionPlanTemplateUsePage, { actionPlanId: 'plan-1' }))

    expect(screen.queryByRole('switch', { name: 'Chronologie par assigné' })).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'Options avancées' }))
    expect(screen.getByRole('switch', { name: 'Chronologie par assigné' })).toBeTruthy()
  })
})
