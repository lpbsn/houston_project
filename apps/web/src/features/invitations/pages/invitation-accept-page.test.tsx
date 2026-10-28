// @vitest-environment jsdom

import { createElement, type ReactNode } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import sporeIconSrc from '@/assets/brand/spore-icon-green.png'
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

function expectAuthChrome() {
  expect(screen.getByTestId('invitation-accept-page')).toBeTruthy()
  expect(screen.getAllByText('spore')).toHaveLength(1)
  expect(document.querySelector('img')?.getAttribute('src')).toBe(sporeIconSrc)
  expect(screen.queryByText('Rejoignez votre équipe')).toBeNull()
  expect(screen.getByText('© 2026 Spore · Terrain-first')).toBeTruthy()
}

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
    expectAuthChrome()
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
    expectAuthChrome()
    expect(screen.getAllByRole('heading', { name: 'Rejoindre mon équipe' })).toHaveLength(1)
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

  it('names the establishment on the password screen', async () => {
    previewDirectorInvitation.mockResolvedValue({
      requiresPassword: true,
      establishmentName: 'Hôtel des Mésanges',
    })
    renderPage('/invitations#invite-token')
    expect(await screen.findByText(/Hôtel des Mésanges/)).toBeTruthy()
    expect(screen.getByLabelText(/^mot de passe$/i)).toBeTruthy()
    expect(screen.getByLabelText(/confirmer le mot de passe/i)).toBeTruthy()
    expect(screen.getByText('Au moins 12 caractères')).toBeTruthy()
    expect(screen.getByText('Ne doit pas être uniquement composé de chiffres')).toBeTruthy()
    expect(screen.getByText('Les deux champs doivent correspondre')).toBeTruthy()
    expect(screen.getByRole('link', { name: /conditions d’utilisation/i })).toBeTruthy()
    expectAuthChrome()
    expect(screen.getAllByRole('heading', { name: 'Rejoindre mon équipe' })).toHaveLength(1)
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
      userId: 'user-2',
      establishmentId: 'est-2',
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
    expect(history.getHref()).toBe('/login?next=%2Facces')
    expect(JSON.parse(sessionStorage.getItem('spore.access-arrival') ?? 'null')).toEqual({
      userId: 'user-2',
      arrival: 'joined',
      establishmentId: 'est-2',
    })
    expect(onAccepted).not.toHaveBeenCalled()
    expect(logout).not.toHaveBeenCalled()
    expectAuthChrome()
    expect(screen.getByRole('heading', { name: 'Bienvenue dans votre équipe !' })).toBeTruthy()
    expect(screen.queryByLabelText(/^mot de passe$/i)).toBeNull()
  })

  it('keeps another signed-in account in place until that person signs out', async () => {
    getAccessToken.mockReturnValue('other-account-access')
    previewDirectorInvitation.mockResolvedValue({ requiresPassword: false })
    acceptDirectorInvitation.mockResolvedValue({
      kind: 'membership_only',
      requiresLogin: true,
      userId: 'user-2',
      establishmentId: 'est-2',
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
      expect(history.getHref()).toBe('/login?next=%2Facces')
    })
    expect(JSON.parse(sessionStorage.getItem('spore.access-arrival') ?? 'null')).toEqual({
      userId: 'user-2',
      arrival: 'joined',
      establishmentId: 'est-2',
    })
    expectAuthChrome()
  })

  it('keeps the current session when the invited account is already signed in', async () => {
    previewDirectorInvitation.mockResolvedValue({ requiresPassword: false })
    acceptDirectorInvitation.mockResolvedValue({
      kind: 'membership_only',
      requiresLogin: false,
      userId: 'user-1',
      establishmentId: 'est-1',
    })
    const { onAccepted } = renderPage('/invitations#invite-token')

    fireEvent.click(await screen.findByRole('button', { name: 'Rejoindre mon équipe' }))

    await vi.waitFor(() => {
      expect(onAccepted).toHaveBeenCalledOnce()
    })
    expect(screen.queryByText('Bienvenue dans votre équipe !')).toBeNull()
    expect(JSON.parse(sessionStorage.getItem('spore.access-arrival') ?? 'null')).toEqual({
      userId: 'user-1',
      arrival: 'joined',
      establishmentId: 'est-1',
    })
    const pendingSubmit = screen.getByRole('button', { name: /activation en cours/i })
    expect(pendingSubmit).toHaveProperty('disabled', true)
    fireEvent.submit(pendingSubmit.closest('form')!)
    expect(acceptDirectorInvitation).toHaveBeenCalledTimes(1)
    expect(onAccepted).toHaveBeenCalledOnce()
    expectAuthChrome()
    expect(screen.queryByLabelText(/^mot de passe$/i)).toBeNull()
  })

  it('keeps the join form inactive after a new account session is created', async () => {
    acceptDirectorInvitation.mockResolvedValue({
      kind: 'session',
      userId: 'user-1',
      establishmentId: 'est-1',
    })
    const { onAccepted } = renderPage('/invitations#invite-token')

    fireEvent.change(await screen.findByLabelText(/^mot de passe$/i), {
      target: { value: 'SecurePass123!' },
    })
    fireEvent.change(screen.getByLabelText(/confirmer le mot de passe/i), {
      target: { value: 'SecurePass123!' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Rejoindre mon équipe' }))

    await vi.waitFor(() => {
      expect(onAccepted).toHaveBeenCalledOnce()
    })
    expect(screen.queryByText('Bienvenue dans votre équipe !')).toBeNull()
    expect(JSON.parse(sessionStorage.getItem('spore.access-arrival') ?? 'null')).toEqual({
      userId: 'user-1',
      arrival: 'activated',
      establishmentId: 'est-1',
    })
    const pendingSubmit = screen.getByRole('button', { name: /activation en cours/i })
    expect(pendingSubmit).toHaveProperty('disabled', true)
    fireEvent.submit(pendingSubmit.closest('form')!)
    expect(acceptDirectorInvitation).toHaveBeenCalledTimes(1)
    expect(onAccepted).toHaveBeenCalledOnce()
    expectAuthChrome()
    expect(screen.getByLabelText(/^mot de passe$/i)).toBeTruthy()
    expect(screen.getByLabelText(/confirmer le mot de passe/i)).toBeTruthy()
  })

  it('shows an expired invitation without password fields or an active submit', async () => {
    previewDirectorInvitation.mockRejectedValue(new InvitationAcceptApiError('Expired', 400, 'invitation_expired'))
    renderPage('/invitations#expired-token')
    expect(await screen.findByRole('alert')).toHaveProperty('textContent', 'Cette invitation a expiré. Demandez une nouvelle invitation à votre responsable.')
    expect(screen.queryByLabelText(/^mot de passe$/i)).toBeNull()
    expect(screen.getByRole('button', { name: 'Rejoindre mon équipe' })).toHaveProperty('disabled', true)
    expect(acceptDirectorInvitation).not.toHaveBeenCalled()
    expectAuthChrome()
  })

  it('shows the server message when password validation fails', async () => {
    acceptDirectorInvitation.mockRejectedValueOnce(
      new InvitationAcceptApiError('Ce mot de passe est trop courant.', 400, 'validation_error'),
    )
    renderPage('/invitations#invite-token')

    fireEvent.change(await screen.findByLabelText(/^mot de passe$/i), {
      target: { value: 'SecurePass123!' },
    })
    fireEvent.change(screen.getByLabelText(/confirmer le mot de passe/i), {
      target: { value: 'SecurePass123!' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Rejoindre mon équipe' }))

    expect(await screen.findByRole('alert')).toHaveProperty(
      'textContent',
      'Ce mot de passe est trop courant.',
    )
    expect(screen.queryByText(/Vérifiez votre connexion/)).toBeNull()
    expect(screen.queryByText('Bienvenue dans votre équipe !')).toBeNull()
  })

  it('shows a French validation message when the server sends no field error', async () => {
    acceptDirectorInvitation.mockRejectedValueOnce(
      new InvitationAcceptApiError(
        'Les informations saisies ne sont pas valides. Corrigez-les puis réessayez.',
        400,
        'validation_error',
      ),
    )
    renderPage('/invitations#invite-token')

    fireEvent.change(await screen.findByLabelText(/^mot de passe$/i), {
      target: { value: 'SecurePass123!' },
    })
    fireEvent.change(screen.getByLabelText(/confirmer le mot de passe/i), {
      target: { value: 'SecurePass123!' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Rejoindre mon équipe' }))

    expect(await screen.findByRole('alert')).toHaveProperty(
      'textContent',
      'Les informations saisies ne sont pas valides. Corrigez-les puis réessayez.',
    )
    expect(screen.queryByText('Request validation failed.')).toBeNull()
    expect(screen.queryByText(/Vérifiez votre connexion/)).toBeNull()
  })

  it('does not show success after a rejected acceptance and permits retry', async () => {
    previewDirectorInvitation.mockResolvedValue({ requiresPassword: false })
    acceptDirectorInvitation.mockRejectedValueOnce(new Error('Network unavailable'))
    const { onAccepted } = renderPage('/invitations#invite-token')
    fireEvent.click(await screen.findByRole('button', { name: 'Rejoindre mon équipe' }))
    expect((await screen.findByRole('alert')).textContent).toContain('Vérifiez votre connexion')
    expect(screen.queryByText('Bienvenue dans votre équipe !')).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'Rejoindre mon équipe' }))
    await vi.waitFor(() => {
      expect(onAccepted).toHaveBeenCalledOnce()
    })
    expect(screen.queryByText('Bienvenue dans votre équipe !')).toBeNull()
    expect(acceptDirectorInvitation).toHaveBeenCalledTimes(2)
  })

})
