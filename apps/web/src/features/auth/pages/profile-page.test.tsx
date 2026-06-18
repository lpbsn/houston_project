// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ProfilePage } from './profile-page'

const onNavigate = vi.fn()
const onSignOut = vi.fn()

const { authState } = vi.hoisted(() => ({
  authState: {
    current: {
      activeMembership: {
        id: 'member-1',
        establishment_id: 'est-1',
        establishment_name: 'Le Palais Nancy',
        role: 'director',
        status: 'active',
      },
      bootstrap: {
        permission_hints: {
          chat_available: false,
          can_create_action: false,
          can_create_checklist_template: true,
          can_invite: true,
          can_manage_runtime_config: true,
        },
      },
      user: {
        first_name: 'Marie',
        last_name: 'Renaud',
        email: 'marie@example.com',
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
  onSignOut.mockReset()
})

describe('ProfilePage', () => {
  it('shows loading state while bootstrapping', () => {
    authState.current = {
      ...authState.current,
      isBootstrapping: true,
      isReady: false,
    }

    render(
      createElement(ProfilePage, {
        onNavigate,
        onSignOut,
      }),
    )

    expect(screen.getByText('Chargement du profil...')).toBeTruthy()
  })

  it('renders user card with name, initials, and role badge', () => {
    authState.current = {
      ...authState.current,
      isBootstrapping: false,
      isReady: true,
    }

    render(
      createElement(ProfilePage, {
        onNavigate,
        onSignOut,
      }),
    )

    expect(screen.getByText('Marie Renaud')).toBeTruthy()
    expect(screen.getByText('Directeur · Le Palais Nancy')).toBeTruthy()
    expect(screen.getAllByText('DIRECTEUR').length).toBeGreaterThan(0)
  })

  it('toggles notification placeholders locally', () => {
    render(
      createElement(ProfilePage, {
        onNavigate,
        onSignOut,
      }),
    )

    const signalSwitch = screen.getByRole('switch', { name: 'Notifications signaux' })
    expect(signalSwitch.getAttribute('aria-checked')).toBe('true')

    fireEvent.click(signalSwitch)
    expect(signalSwitch.getAttribute('aria-checked')).toBe('false')

    const executionSwitch = screen.getByRole('switch', { name: 'Notifications exécutions' })
    fireEvent.click(executionSwitch)
    expect(executionSwitch.getAttribute('aria-checked')).toBe('false')
  })

  it('hides management section when permission hints deny access', () => {
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
    }

    render(
      createElement(ProfilePage, {
        onNavigate,
        onSignOut,
      }),
    )

    expect(screen.queryByText("Gestion de l'établissement")).toBeNull()
    expect(screen.queryByText('Établissement')).toBeNull()
  })

  it('shows management cards and navigates on click', () => {
    authState.current = {
      ...authState.current,
      bootstrap: {
        permission_hints: {
          chat_available: false,
          can_create_action: false,
          can_create_checklist_template: true,
          can_invite: true,
          can_manage_runtime_config: true,
        },
      },
    }

    render(
      createElement(ProfilePage, {
        onNavigate,
        onSignOut,
      }),
    )

    fireEvent.click(screen.getByRole('button', { name: /Établissement/i }))
    expect(onNavigate).toHaveBeenCalledWith('/app/operational-config')

    fireEvent.click(screen.getByRole('button', { name: /Listes/i }))
    expect(onNavigate).toHaveBeenCalledWith('/checklists')

    fireEvent.click(screen.getByRole('button', { name: /Équipe/i }))
    expect(onNavigate).toHaveBeenCalledWith('/team')
  })

  it('hides establishment card when runtime config hint is false', () => {
    authState.current = {
      ...authState.current,
      bootstrap: {
        permission_hints: {
          chat_available: false,
          can_create_action: false,
          can_create_checklist_template: false,
          can_invite: true,
          can_manage_runtime_config: false,
        },
      },
    }

    render(
      createElement(ProfilePage, {
        onNavigate,
        onSignOut,
      }),
    )

    expect(screen.queryByRole('button', { name: /Établissement/i })).toBeNull()
    expect(screen.getByRole('button', { name: /Équipe/i })).toBeTruthy()
  })

  it('calls onSignOut from logout button', () => {
    render(
      createElement(ProfilePage, {
        onNavigate,
        onSignOut,
      }),
    )

    fireEvent.click(screen.getByRole('button', { name: 'Se déconnecter' }))
    expect(onSignOut).toHaveBeenCalledTimes(1)
  })
})
