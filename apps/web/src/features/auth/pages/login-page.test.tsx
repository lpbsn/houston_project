// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { LoginPage } from './login-page'

const onNavigate = vi.fn()
const authState = vi.hoisted(() => ({
  isReady: true,
}))

vi.mock('@/app/auth-provider', () => ({
  useAuth: () => ({
    isReady: authState.isReady,
  }),
}))

vi.mock('@/features/auth/components/login-form', () => ({
  LoginForm: () => createElement('div', { 'data-testid': 'login-form-stub' }, 'Se connecter'),
}))

afterEach(() => {
  cleanup()
  onNavigate.mockReset()
  authState.isReady = true
})

describe('LoginPage', () => {
  it('renders the spore wordmark and icon', () => {
    render(createElement(LoginPage, { onNavigate }))

    expect(screen.getByText('spore')).toBeTruthy()
    expect(screen.getByTestId('login-page')).toBeTruthy()
  })

  it('renders the Spore footer', () => {
    render(createElement(LoginPage, { onNavigate }))

    expect(screen.getByText('© 2026 Spore · Terrain-first')).toBeTruthy()
  })

  it('renders the Onboarding button and navigates to /onboarding', () => {
    render(createElement(LoginPage, { onNavigate }))

    fireEvent.click(screen.getByRole('button', { name: 'Onboarding' }))

    expect(onNavigate).toHaveBeenCalledWith('/onboarding')
  })

  it('renders session-restore loading UI when auth is not ready', () => {
    authState.isReady = false

    render(createElement(LoginPage, { onNavigate }))

    expect(screen.getByTestId('login-page')).toBeTruthy()
    expect(screen.getByText('Restauration de votre session…')).toBeTruthy()
  })

  it('does not render the login form while auth is restoring', () => {
    authState.isReady = false

    render(createElement(LoginPage, { onNavigate }))

    expect(screen.queryByTestId('login-form-stub')).toBeNull()
    expect(screen.queryByText('Se connecter')).toBeNull()
  })
})
