// @vitest-environment jsdom

import { createElement, type ReactNode } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { AppRouteProvider } from '@/app/app-routes'
import { createMemoryHistory } from '@/app/app-history'

const acceptDirectorInvitation = vi.hoisted(() => vi.fn())

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
}))

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
  acceptDirectorInvitation.mockResolvedValue(undefined)
})

describe('InvitationAcceptPage', () => {
  it('moves the fragment secret into memory and strips it from the URL', () => {
    const { history } = renderPage('/invitations#invite-token')

    expect(history.getHref()).toBe('/invitations')
    expect(screen.queryByLabelText('Invitation code')).toBeNull()
  })

  it('shows a code field when the fragment is missing', () => {
    renderPage('/invitations')

    expect(screen.getByLabelText('Invitation code')).toBeTruthy()
  })

  it('does not treat a path segment as an invitation secret', () => {
    const { history } = renderPage('/invitations/legacy-token')

    expect(history.getHref()).toBe('/invitations/legacy-token')
    expect(screen.getByLabelText('Invitation code')).toBeTruthy()
  })

  it('submits the remembered fragment token in the accept call', async () => {
    renderPage('/invitations#invite-token')

    fireEvent.change(screen.getByLabelText(/^mot de passe$/i), { target: { value: 'SecurePass123!' } })
    fireEvent.change(screen.getByLabelText(/confirmer le mot de passe/i), {
      target: { value: 'SecurePass123!' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Accept invitation' }))

    await vi.waitFor(() => {
      expect(acceptDirectorInvitation).toHaveBeenCalledWith('invite-token', {
        password: 'SecurePass123!',
        password_confirmation: 'SecurePass123!',
      })
    })
  })

  it('does not submit when confirmation does not match', () => {
    renderPage('/invitations#invite-token')
    fireEvent.change(screen.getByLabelText(/^mot de passe$/i), { target: { value: 'SecurePass123!' } })
    fireEvent.change(screen.getByLabelText(/confirmer le mot de passe/i), {
      target: { value: 'DifferentPass12' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Accept invitation' }))
    expect(acceptDirectorInvitation).not.toHaveBeenCalled()
  })
})
