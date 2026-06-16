// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ChecklistCreatePage } from './checklist-create-page'

const navigate = vi.fn()
const createTemplateMutateAsync = vi.fn()
const createAssignmentMutateAsync = vi.fn()

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

vi.mock('@/features/auth/hooks', () => ({
  useBusinessUnitTreeQuery: () => ({
    data: {
      business_units: [{ id: 'bu-1', label: 'Rooftop', key: 'rooftop' }],
    },
    isLoading: false,
    isError: false,
  }),
}))

vi.mock('@/features/actions/hooks', () => ({
  useEstablishmentUserSearchQuery: () => ({
    data: [],
    isLoading: false,
    isError: false,
  }),
}))

vi.mock('@/features/checklists/hooks', () => ({
  useCreateChecklistTemplateMutation: () => ({
    mutateAsync: createTemplateMutateAsync,
    isPending: false,
  }),
  useCreateChecklistAssignmentForTemplateMutation: () => ({
    mutateAsync: createAssignmentMutateAsync,
    isPending: false,
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
      createElement(ChecklistCreatePage, {
        backPath: '/checklists',
      }),
    ),
  )
}

async function selectBusinessUnit() {
  fireEvent.click(screen.getByRole('button', { name: "Pôle d'activité" }))
  await waitFor(() => {
    expect(screen.getByRole('button', { name: 'Rooftop' })).toBeTruthy()
  })
  fireEvent.click(screen.getByRole('button', { name: 'Rooftop' }))
}

async function fillMinimumForm() {
  fireEvent.change(screen.getByPlaceholderText('To do ouverture'), {
    target: { value: 'To do ouverture' },
  })
  fireEvent.change(screen.getByPlaceholderText('Ex. Désactiver l’alarme'), {
    target: { value: 'Désactiver l’alarme' },
  })
  await selectBusinessUnit()
}

describe('ChecklistCreatePage', () => {
  beforeEach(() => {
    navigate.mockReset()
    createTemplateMutateAsync.mockReset()
    createAssignmentMutateAsync.mockReset()

    createTemplateMutateAsync.mockResolvedValue({ id: 'tpl-1' })
    createAssignmentMutateAsync.mockResolvedValue({ id: 'assign-1' })
  })

  afterEach(() => {
    cleanup()
  })

  it('renders local header actions', () => {
    renderPage()
    expect(screen.getByRole('button', { name: 'Annuler' })).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Nouvelle liste' })).toBeTruthy()
    expect(screen.getAllByRole('button', { name: 'Créer' })).toHaveLength(1)
  })

  it('renders business unit field before title', () => {
    renderPage()
    const businessUnitField = screen.getByRole('button', { name: "Pôle d'activité" })
    const titleInput = screen.getByPlaceholderText('To do ouverture')

    expect(businessUnitField.compareDocumentPosition(titleInput)).toBe(
      Node.DOCUMENT_POSITION_FOLLOWING,
    )
  })

  it('submits template without assignment with assign_now false', async () => {
    renderPage()
    await fillMinimumForm()
    fireEvent.click(screen.getByRole('button', { name: 'Créer' }))

    await waitFor(() => {
      expect(createTemplateMutateAsync).toHaveBeenCalledWith({
        title: 'To do ouverture',
        description: '',
        business_unit_id: 'bu-1',
        tasks: [{ task: 'Désactiver l’alarme' }],
        assign_now: false,
      })
    })
    expect(createAssignmentMutateAsync).not.toHaveBeenCalled()
    expect(navigate).toHaveBeenCalledWith('/checklists/tpl-1', { replace: true })
  })

  it('shows validation error when title is missing', async () => {
    renderPage()
    fireEvent.click(screen.getByRole('button', { name: 'Créer' }))

    expect(await screen.findByText('Le titre est obligatoire.')).toBeTruthy()
    expect(createTemplateMutateAsync).not.toHaveBeenCalled()
  })

  it('handles partial assignment failure without recreating template', async () => {
    createAssignmentMutateAsync
      .mockRejectedValueOnce(new Error('assignment failed'))
      .mockResolvedValueOnce({ id: 'assign-1' })

    renderPage()
    await fillMinimumForm()
    fireEvent.click(screen.getByRole('button', { name: 'Options' }))
    await waitFor(() => {
      expect(screen.getByText('Créer une affectation maintenant')).toBeTruthy()
    })
    fireEvent.click(screen.getByRole('button', { name: 'Créer une affectation maintenant' }))
    fireEvent.change(screen.getByLabelText('Date de début'), {
      target: { value: '2026-06-10' },
    })
    fireEvent.change(screen.getByLabelText('Heure de début'), {
      target: { value: '08:00' },
    })
    fireEvent.change(screen.getByLabelText('Heure de fin'), {
      target: { value: '10:00' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Enregistrer' }))
    fireEvent.click(screen.getByRole('button', { name: 'Créer' }))

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Réessayer l’affectation' })).toBeTruthy()
    })
    expect(createTemplateMutateAsync).toHaveBeenCalledTimes(1)

    fireEvent.click(screen.getByRole('button', { name: 'Réessayer l’affectation' }))

    await waitFor(() => {
      expect(createTemplateMutateAsync).toHaveBeenCalledTimes(1)
      expect(createAssignmentMutateAsync).toHaveBeenCalledTimes(2)
    })
  })
})
