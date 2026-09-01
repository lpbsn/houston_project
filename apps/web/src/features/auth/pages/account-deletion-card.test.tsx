// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { AuthApiError } from '@/features/auth/api'

import { AccountDeletionCard } from './account-deletion-card'

const { fetchAccountDeletionPreview, deleteAccount } = vi.hoisted(() => ({
  fetchAccountDeletionPreview: vi.fn(),
  deleteAccount: vi.fn(),
}))

vi.mock('@/features/auth/api', async () => {
  class AuthApiErrorMock extends Error {
    status: number
    code: string | null
    constructor(message: string, status: number, code: string | null = null) {
      super(message)
      this.name = 'AuthApiError'
      this.status = status
      this.code = code
    }
  }
  return {
    AuthApiError: AuthApiErrorMock,
    fetchAccountDeletionPreview: (...args: unknown[]) => fetchAccountDeletionPreview(...args),
    deleteAccount: (...args: unknown[]) => deleteAccount(...args),
  }
})

const staffPreview = {
  requires_organization_closure: false,
  organizations: [],
  leaves_establishments_without_director: [],
}

const ownerPreview = {
  requires_organization_closure: true,
  organizations: [{ id: 'org-1', name: 'Northwind Group', establishment_names: ['Hotel'] }],
  leaves_establishments_without_director: [],
}

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe('AccountDeletionCard', () => {
  beforeEach(() => {
    fetchAccountDeletionPreview.mockResolvedValue(staffPreview)
    deleteAccount.mockResolvedValue(undefined)
  })

  it('refreshes preview after organization_closure_required so the closure checkbox appears', async () => {
    fetchAccountDeletionPreview
      .mockResolvedValueOnce(staffPreview)
      .mockResolvedValueOnce(ownerPreview)
    deleteAccount.mockRejectedValueOnce(
      new AuthApiError('Account deletion failed.', 409, 'organization_closure_required'),
    )
    const onDeleted = vi.fn()
    render(<AccountDeletionCard onDeleted={onDeleted} />)

    fireEvent.click(screen.getByRole('button', { name: 'Supprimer mon compte' }))
    await waitFor(() => {
      expect(screen.getByPlaceholderText('Mot de passe')).toBeTruthy()
    })

    fireEvent.change(screen.getByPlaceholderText('Mot de passe'), {
      target: { value: 'secret-pass' },
    })
    await waitFor(() => {
      expect(
        (screen.getByRole('button', { name: 'Confirmer la suppression' }) as HTMLButtonElement)
          .disabled,
      ).toBe(false)
    })
    fireEvent.click(screen.getByRole('button', { name: 'Confirmer la suppression' }))

    await waitFor(() => {
      expect(screen.getByRole('checkbox')).toBeTruthy()
    })
    expect(screen.getByText(/Northwind Group/)).toBeTruthy()
    expect(screen.getByText('Cochez la fermeture de votre organisation pour continuer.')).toBeTruthy()
    expect((screen.getByPlaceholderText('Mot de passe') as HTMLInputElement).value).toBe('secret-pass')
    expect(onDeleted).not.toHaveBeenCalled()
    expect(fetchAccountDeletionPreview).toHaveBeenCalledTimes(2)
  })

  it('does not invent organization closure when preview refetch fails after 409', async () => {
    fetchAccountDeletionPreview
      .mockResolvedValueOnce(staffPreview)
      .mockRejectedValueOnce(new Error('preview down'))
    deleteAccount.mockRejectedValueOnce(
      new AuthApiError('Account deletion failed.', 409, 'organization_closure_required'),
    )
    render(<AccountDeletionCard onDeleted={vi.fn()} />)

    fireEvent.click(screen.getByRole('button', { name: 'Supprimer mon compte' }))
    await waitFor(() => {
      expect(screen.getByPlaceholderText('Mot de passe')).toBeTruthy()
    })

    fireEvent.change(screen.getByPlaceholderText('Mot de passe'), {
      target: { value: 'secret-pass' },
    })
    await waitFor(() => {
      expect(
        (screen.getByRole('button', { name: 'Confirmer la suppression' }) as HTMLButtonElement)
          .disabled,
      ).toBe(false)
    })
    fireEvent.click(screen.getByRole('button', { name: 'Confirmer la suppression' }))

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Recharger les conséquences' })).toBeTruthy()
    })
    expect(screen.queryByRole('checkbox')).toBeNull()
    expect(screen.getByText('Impossible de recharger les conséquences de la suppression.')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Confirmer la suppression' })).toHaveProperty(
      'disabled',
      true,
    )
  })
})
