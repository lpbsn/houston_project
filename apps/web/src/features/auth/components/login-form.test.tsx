// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { AuthApiError } from '@/features/auth/api'
import { LoginForm } from './login-form'

const login = vi.fn(async () => undefined)
const authState = vi.hoisted(() => ({
  isLoggingIn: false,
  loginError: null as Error | null,
}))

vi.mock('@/app/auth-provider', () => ({
  useAuth: () => ({
    isLoggingIn: authState.isLoggingIn,
    login,
    loginError: authState.loginError,
  }),
}))

afterEach(() => {
  cleanup()
  login.mockClear()
  authState.isLoggingIn = false
  authState.loginError = null
})

describe('LoginForm', () => {
  it('renders French labels and placeholder', () => {
    render(createElement(LoginForm))

    expect(screen.getByLabelText('Email ou identifiant')).toBeTruthy()
    expect(screen.getByLabelText('Mot de passe')).toBeTruthy()
    expect(screen.getByPlaceholderText('vous@spore.app')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Se connecter' })).toBeTruthy()
    expect(screen.queryByText('Oublié ?')).toBeNull()
  })

  it('toggles password visibility', () => {
    render(createElement(LoginForm))

    const passwordInput = screen.getByLabelText('Mot de passe') as HTMLInputElement
    const toggle = screen.getByRole('button', { name: 'Afficher le mot de passe' })

    expect(passwordInput.type).toBe('password')

    fireEvent.click(toggle)

    expect(passwordInput.type).toBe('text')
    expect(screen.getByRole('button', { name: 'Masquer le mot de passe' })).toBeTruthy()
  })

  it('submits trimmed identifier and password via useAuth.login', async () => {
    render(createElement(LoginForm))

    fireEvent.change(screen.getByLabelText('Email ou identifiant'), {
      target: { value: '  owner@example.com  ' },
    })
    fireEvent.change(screen.getByLabelText('Mot de passe'), {
      target: { value: 'secret' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Se connecter' }))

    expect(login).toHaveBeenCalledWith({
      identifier: 'owner@example.com',
      password: 'secret',
    })
  })

  it('shows French invalid credentials message on 401', () => {
    authState.loginError = new AuthApiError('Unauthorized', 401)

    render(createElement(LoginForm))

    expect(screen.getByText('Identifiants invalides.')).toBeTruthy()
  })

  it('shows generic French error message for other failures', () => {
    authState.loginError = new Error('Network error')

    render(createElement(LoginForm))

    expect(screen.getByText('La connexion a échoué.')).toBeTruthy()
  })
})
