// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ActionCreatePage } from './action-create-page'

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
        can_create_action: true,
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

const mockUsers = [
  {
    membership_id: 'member-1',
    display_name: 'Marie Dupont',
    role: 'staff',
    username: 'marie',
  },
  {
    membership_id: 'member-2',
    display_name: 'Jean Martin',
    role: 'manager',
    username: 'jean',
  },
]

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

vi.mock('@/features/actions/hooks', () => ({
  useEstablishmentUserSearchQuery: (_establishmentId: string, query: string) => ({
    data: query.trim().length >= 2 ? mockUsers : [],
    isFetching: false,
  }),
  useCreateActionMutation: () => ({
    mutateAsync: createMutateAsync,
    isPending: false,
    error: null,
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
      createElement(ActionCreatePage, {
        mode: 'free',
        onNavigate: navigate,
      }),
    ),
  )
}

async function fillRequiredFields() {
  fireEvent.click(screen.getByRole('button', { name: 'Rooftop' }))
  fireEvent.change(screen.getByPlaceholderText('Ex. Vérifier la climatisation'), {
    target: { value: 'Vérifier la clim' },
  })
  fireEvent.change(screen.getByPlaceholderText('Décrivez la consigne pour le responsable…'), {
    target: { value: 'Consigne détaillée' },
  })
}

async function searchAndSelectUser(displayName: string) {
  const searchInput = screen.getByPlaceholderText('Rechercher un membre…')
  fireEvent.change(searchInput, { target: { value: displayName.slice(0, 2) } })
  await waitFor(() => {
    expect(screen.getByRole('option', { name: new RegExp(displayName, 'i') })).toBeTruthy()
  })
  fireEvent.click(screen.getByRole('button', { name: new RegExp(displayName, 'i') }))
}

describe('ActionCreatePage', () => {
  beforeEach(() => {
    navigate.mockReset()
    createMutateAsync.mockReset()
    createMutateAsync.mockResolvedValue({ id: 'action-1' })
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

  it('disables submit when no assignee is selected', async () => {
    renderPage()
    await fillRequiredFields()

    const submitButton = screen.getByRole('button', { name: 'Créer' })
    expect(submitButton).toHaveProperty('disabled', true)
  })

  it('supports multi-assignee selection and submit', async () => {
    renderPage()
    await fillRequiredFields()
    await searchAndSelectUser('Marie Dupont')
    await searchAndSelectUser('Jean Martin')

    expect(screen.getByLabelText('Membres sélectionnés').children).toHaveLength(2)

    const submitButton = screen.getByRole('button', { name: 'Créer' })
    expect(submitButton).toHaveProperty('disabled', false)

    fireEvent.click(submitButton)

    await waitFor(() => {
      expect(createMutateAsync).toHaveBeenCalledTimes(1)
    })

    expect(createMutateAsync).toHaveBeenCalledWith(
      expect.objectContaining({
        assignee_ids: ['member-1', 'member-2'],
        requires_validation: true,
        title: 'Vérifier la clim',
        instruction: 'Consigne détaillée',
        signal: null,
        responsible_business_unit_id: 'bu-1',
      }),
    )
  })

  it('allows removing a selected assignee before submit', async () => {
    renderPage()
    await fillRequiredFields()
    await searchAndSelectUser('Marie Dupont')
    await searchAndSelectUser('Jean Martin')

    fireEvent.click(screen.getByRole('button', { name: 'Retirer Jean Martin' }))

    expect(screen.getByLabelText('Membres sélectionnés').children).toHaveLength(1)

    fireEvent.click(screen.getByRole('button', { name: 'Créer' }))

    await waitFor(() => {
      expect(createMutateAsync).toHaveBeenCalledWith(
        expect.objectContaining({
          assignee_ids: ['member-1'],
        }),
      )
    })
  })

  it('sends requires_validation=false when toggle is turned off', async () => {
    renderPage()
    await fillRequiredFields()
    await searchAndSelectUser('Marie Dupont')

    fireEvent.click(screen.getByRole('switch', { name: 'Validation requise' }))
    fireEvent.click(screen.getByRole('button', { name: 'Créer' }))

    await waitFor(() => {
      expect(createMutateAsync).toHaveBeenCalledWith(
        expect.objectContaining({
          requires_validation: false,
        }),
      )
    })
  })

  it('defaults requires_validation to true without toggling', async () => {
    renderPage()

    expect(screen.getByRole('switch', { name: 'Validation requise' }).getAttribute('aria-checked')).toBe(
      'true',
    )

    await fillRequiredFields()
    await searchAndSelectUser('Marie Dupont')
    fireEvent.click(screen.getByRole('button', { name: 'Créer' }))

    await waitFor(() => {
      expect(createMutateAsync).toHaveBeenCalledWith(
        expect.objectContaining({
          requires_validation: true,
        }),
      )
    })
  })

  it('locks staff to self assignee and submits assignee_ids with membership id', async () => {
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

    renderPage()
    await fillRequiredFields()

    expect(screen.queryByPlaceholderText('Rechercher un membre…')).toBeNull()
    expect(screen.queryByLabelText('Membres sélectionnés')).toBeNull()
    expect(screen.getByText('staff_user')).toBeTruthy()

    const submitButton = screen.getByRole('button', { name: 'Créer' })
    expect(submitButton).toHaveProperty('disabled', false)

    fireEvent.click(submitButton)

    await waitFor(() => {
      expect(createMutateAsync).toHaveBeenCalledWith(
        expect.objectContaining({
          assignee_ids: ['staff-member-1'],
          signal: null,
          responsible_business_unit_id: 'bu-1',
        }),
      )
    })
  })
})
