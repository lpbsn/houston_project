// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ActionPlanCreatePage } from './action-plan-create-page'

const navigate = vi.fn()
const createMutateAsync = vi.fn()

const { mockAuthState } = vi.hoisted(() => ({
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
        can_create_action: true,
        can_create_checklist_template: false,
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
    data: {
      business_units: [{ id: 'bu-1', label: 'Rooftop', key: 'rooftop', unit_type: 'service' }],
    },
    isLoading: false,
    isError: false,
  }),
}))

vi.mock('../hooks', () => ({
  useCreateActionPlanMutation: () => ({
    mutateAsync: createMutateAsync,
    isPending: false,
  }),
}))

vi.mock('../components/action-plan-assignee-chronology-sheet', () => ({
  ActionPlanAssigneeChronologySheet: () => null,
}))

function renderPage(props: { mode?: 'catalog' | 'execution'; backPath?: string } = {}) {
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
    createMutateAsync.mockResolvedValue({ id: 'exec-1', object_type: 'action_plan_execution' })

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
      can_create_action: true,
      can_create_checklist_template: false,
      can_invite: false,
      can_manage_runtime_config: false,
    }
    mockAuthState.activeMembership = {
      id: 'member-manager',
      establishment_id: 'est-1',
      role: 'manager',
      scopes: [],
    }
  })

  afterEach(() => {
    cleanup()
  })

  it('submits catalog create with is_reusable true when save to library is enabled', async () => {
    renderPage({ mode: 'catalog' })

    const textInputs = screen.getAllByRole('textbox')
    fireEvent.change(textInputs[0], { target: { value: 'Plan catalogue' } })
    fireEvent.change(screen.getByLabelText('Tâche'), { target: { value: 'Task 1' } })
    fireEvent.click(screen.getByRole('checkbox', { name: 'Enregistrer dans la bibliothèque' }))
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
    fireEvent.change(screen.getByLabelText('Tâche'), { target: { value: 'Tâche 1' } })

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
})
