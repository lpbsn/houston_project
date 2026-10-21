// @vitest-environment jsdom

import { createElement, type ReactNode } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { AppRouteProvider } from '@/app/app-routes'
import { createMemoryHistory } from '@/app/app-history'

const acceptDirectorInvitation = vi.hoisted(() => vi.fn())
const previewDirectorInvitation = vi.hoisted(() => vi.fn())
const getAccessToken = vi.hoisted(() => vi.fn(() => null as string | null))
const logout = vi.hoisted(() => vi.fn(async () => undefined))
const clearAuthState = vi.hoisted(() => vi.fn())

vi.mock('@/features/auth/api', () => ({
  logout,
  clearAuthState,
}))

vi.mock('@/features/auth/session', () => ({
  getAccessToken,
}))

vi.mock('@/features/invitations/api', () => ({
  InvitationAcceptApiError: class InvitationAcceptApiError extends Error {
    status: number
    code: string | null

    constructor(message: string, status: number, code: string | null = null) {
      super(message)
      this.name = 'InvitationAcceptApiError'
      this.status = status
      this.code = code
    }
  },
  acceptDirectorInvitation,
  previewDirectorInvitation,
}))

import { InvitationAcceptApiError } from '@/features/invitations/api'

import { InvitationAcceptPage } from './invitation-accept-page'

function renderPage(initialHref: string, onAccepted = vi.fn()) {
  const history = createMemoryHistory(initialHref)
  function Wrapper({ children }: { children: ReactNode }) {
    return createElement(AppRouteProvider, { history }, children)
  }
  render(createElement(InvitationAcceptPage, { onAccepted }), { wrapper: Wrapper })
  return { history, onAccepted }
}

afterEach(() => {
  cleanup()
})

beforeEach(() => {
  acceptDirectorInvitation.mockReset()
  acceptDirectorInvitation.mockResolvedValue({ kind: 'session' })
  previewDirectorInvitation.mockReset()
  previewDirectorInvitation.mockResolvedValue({ requiresPassword: true })
  getAccessToken.mockReset()
  getAccessToken.mockReturnValue(null)
  logout.mockReset()
  logout.mockResolvedValue(undefined)
  clearAuthState.mockReset()
})

describe('InvitationAcceptPage', () => {
  it('moves the fragment secret into memory and strips it from the URL', () => {
    const { history } = renderPage('/invitations#invite-token')

    expect(history.getHref()).toBe('/invitations')
    expect(screen.queryByLabelText('Invitation code')).toBeNull()
  })

  it('shows a missing-link state when the fragment is absent', () => {
    const { history } = renderPage('/invitations')

    expect(screen.queryByLabelText('Invitation code')).toBeNull()
    expect(screen.queryByLabelText(/^mot de passe$/i)).toBeNull()
    expect(
      screen.getByText(
        'Ce lien est absent ou invalide. Ouvrez le lien reçu par e-mail pour rejoindre votre équipe.',
      ),
    ).toBeTruthy()
    expect(acceptDirectorInvitation).not.toHaveBeenCalled()

    fireEvent.click(screen.getByRole('button', { name: 'Se connecter' }))
    expect(history.getHref()).toBe('/login')
  })

  it('does not treat a path segment as an invitation secret', () => {
    const { history } = renderPage('/invitations/legacy-token')

    expect(history.getHref()).toBe('/invitations/legacy-token')
    expect(screen.queryByLabelText('Invitation code')).toBeNull()
    expect(screen.queryByLabelText(/^mot de passe$/i)).toBeNull()
    expect(
      screen.getByText(
        'Ce lien est absent ou invalide. Ouvrez le lien reçu par e-mail pour rejoindre votre équipe.',
      ),
    ).toBeTruthy()
    expect(acceptDirectorInvitation).not.toHaveBeenCalled()
  })

  it('submits the remembered fragment token in the accept call', async () => {
    renderPage('/invitations#invite-token')

    fireEvent.change(await screen.findByLabelText(/^mot de passe$/i), {
      target: { value: 'SecurePass123!' },
    })
    fireEvent.change(screen.getByLabelText(/confirmer le mot de passe/i), {
      target: { value: 'SecurePass123!' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Rejoindre mon équipe' }))

    await vi.waitFor(() => {
      expect(acceptDirectorInvitation).toHaveBeenCalledWith('invite-token', {
        password: 'SecurePass123!',
        password_confirmation: 'SecurePass123!',
      })
    })
  })

  it('does not submit when confirmation does not match', async () => {
    renderPage('/invitations#invite-token')
    fireEvent.change(await screen.findByLabelText(/^mot de passe$/i), {
      target: { value: 'SecurePass123!' },
    })
    fireEvent.change(screen.getByLabelText(/confirmer le mot de passe/i), {
      target: { value: 'DifferentPass12' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Rejoindre mon équipe' }))
    expect(acceptDirectorInvitation).not.toHaveBeenCalled()
  })

  it('accepts an existing account without a password and sends an anonymous visitor to login', async () => {
    previewDirectorInvitation.mockResolvedValue({ requiresPassword: false })
    acceptDirectorInvitation.mockResolvedValue({
      kind: 'membership_only',
      requiresLogin: true,
    })
    const { history, onAccepted } = renderPage('/invitations#invite-token')

    expect(screen.queryByLabelText(/^mot de passe$/i)).toBeNull()
    fireEvent.click(await screen.findByRole('button', { name: 'Rejoindre mon équipe' }))

    await vi.waitFor(() => {
      expect(acceptDirectorInvitation).toHaveBeenCalledWith('invite-token', {})
      expect(screen.getByText('Bienvenue dans votre équipe !')).toBeTruthy()
    })
    expect(history.getHref()).toBe('/invitations')
    fireEvent.click(screen.getByRole('button', { name: 'Se connecter à Spore' }))
    expect(history.getHref()).toBe('/login')
    expect(onAccepted).not.toHaveBeenCalled()
    expect(logout).not.toHaveBeenCalled()
  })

  it('keeps another signed-in account in place until that person signs out', async () => {
    getAccessToken.mockReturnValue('other-account-access')
    previewDirectorInvitation.mockResolvedValue({ requiresPassword: false })
    acceptDirectorInvitation.mockResolvedValue({
      kind: 'membership_only',
      requiresLogin: true,
    })
    const { history, onAccepted } = renderPage('/invitations#invite-token')

    fireEvent.click(await screen.findByRole('button', { name: 'Rejoindre mon équipe' }))

    await vi.waitFor(() => {
      expect(screen.getByText(/acceptée pour un autre compte/i)).toBeTruthy()
    })
    expect(history.getHref()).toBe('/invitations')
    expect(onAccepted).not.toHaveBeenCalled()

    fireEvent.click(screen.getByRole('button', { name: 'Changer de compte et continuer' }))

    await vi.waitFor(() => {
      expect(logout).toHaveBeenCalledOnce()
      expect(clearAuthState).toHaveBeenCalledOnce()
      expect(history.getHref()).toBe('/login')
    })
  })

  it('keeps the current session when the invited account is already signed in', async () => {
    previewDirectorInvitation.mockResolvedValue({ requiresPassword: false })
    acceptDirectorInvitation.mockResolvedValue({
      kind: 'membership_only',
      requiresLogin: false,
    })
    const { onAccepted } = renderPage('/invitations#invite-token')

    fireEvent.click(await screen.findByRole('button', { name: 'Rejoindre mon équipe' }))

    await screen.findByText('Bienvenue dans votre équipe !')
    expect(onAccepted).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'Ouvrir mon espace Spore' }))
    expect(onAccepted).toHaveBeenCalledOnce()
  })
  it('shows an expired invitation without password fields or an active submit', async () => {
    previewDirectorInvitation.mockRejectedValue(new InvitationAcceptApiError('Expired', 400, 'invitation_expired'))
    renderPage('/invitations#expired-token')
    expect(await screen.findByRole('alert')).toHaveProperty('textContent', 'Cette invitation a expiré. Demandez une nouvelle invitation à votre responsable.')
    expect(screen.queryByLabelText(/^mot de passe$/i)).toBeNull()
    expect(screen.getByRole('button', { name: 'Rejoindre mon équipe' })).toHaveProperty('disabled', true)
    expect(acceptDirectorInvitation).not.toHaveBeenCalled()
  })

  it('does not show success after a rejected acceptance and permits retry', async () => {
    previewDirectorInvitation.mockResolvedValue({ requiresPassword: false })
    acceptDirectorInvitation.mockRejectedValueOnce(new Error('Network unavailable'))
    renderPage('/invitations#invite-token')
    fireEvent.click(await screen.findByRole('button', { name: 'Rejoindre mon équipe' }))
    await screen.findByRole('alert')
    expect(screen.queryByText('Bienvenue dans votre équipe !')).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'Rejoindre mon équipe' }))
    await screen.findByText('Bienvenue dans votre équipe !')
    expect(acceptDirectorInvitation).toHaveBeenCalledTimes(2)
  })

})
