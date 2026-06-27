// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { TeamPage } from './team-page'

const onNavigate = vi.fn()

const { authState } = vi.hoisted(() => ({
  authState: {
    current: {
      bootstrap: {
        permission_hints: {
          chat_available: false,
          can_create_action: false,
          can_create_checklist_template: false,
          can_invite: true,
          can_manage_runtime_config: false,
        },
      },
      isBootstrapping: false,
      isReady: true,
    },
  },
}))

vi.mock('@/app/auth-provider', () => ({
  useAuth: () => authState.current,
}))

afterEach(() => {
  cleanup()
  onNavigate.mockReset()
})

describe('TeamPage', () => {
  it('shows loading state while bootstrapping', () => {
    authState.current = {
      ...authState.current,
      isBootstrapping: true,
      isReady: false,
    }

    render(createElement(TeamPage, { onNavigate }))

    expect(screen.getByText('Chargement...')).toBeTruthy()
  })

  it('renders members coming soon placeholder', () => {
    authState.current = {
      ...authState.current,
      isBootstrapping: false,
      isReady: true,
    }

    render(createElement(TeamPage, { onNavigate }))

    expect(screen.getByText('Membres')).toBeTruthy()
    expect(
      screen.getByText("La gestion des membres de l'équipe sera disponible prochainement."),
    ).toBeTruthy()
  })

  it('shows invite card when can_invite and navigates to invite route', () => {
    render(createElement(TeamPage, { onNavigate }))

    fireEvent.click(screen.getByRole('button', { name: /Inviter un membre/i }))
    expect(onNavigate).toHaveBeenCalledWith('/team/invite')
  })

  it('hides invite card when can_invite is false but runtime config access remains', () => {
    authState.current = {
      ...authState.current,
      bootstrap: {
        permission_hints: {
          chat_available: false,
          can_create_action: false,
          can_create_checklist_template: false,
          can_invite: false,
          can_manage_runtime_config: true,
        },
      },
      isBootstrapping: false,
      isReady: true,
    }

    render(createElement(TeamPage, { onNavigate }))

    expect(screen.queryByRole('button', { name: /Inviter un membre/i })).toBeNull()
    expect(screen.getByText('Membres')).toBeTruthy()
  })

  it('shows permission denied when management hints are false', () => {
    authState.current = {
      ...authState.current,
      bootstrap: {
        permission_hints: {
          chat_available: false,
          can_create_action: false,
          can_create_checklist_template: false,
          can_invite: false,
          can_manage_runtime_config: false,
        },
      },
      isBootstrapping: false,
      isReady: true,
    }

    render(createElement(TeamPage, { onNavigate }))

    expect(screen.getByText("Vous n'avez pas accès à la gestion d'équipe.")).toBeTruthy()
    expect(screen.getByRole('alert')).toBeTruthy()
    expect(screen.queryByText('Membres')).toBeNull()
    expect(screen.queryByRole('button', { name: /Inviter un membre/i })).toBeNull()

    fireEvent.click(screen.getByRole('button', { name: 'Retour au profil' }))
    expect(onNavigate).toHaveBeenCalledWith('/profile')
  })
})
