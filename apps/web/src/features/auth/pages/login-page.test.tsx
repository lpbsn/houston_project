// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { LoginPage } from './login-page'

const onNavigate = vi.fn()

vi.mock('@/app/auth-provider', () => ({
  useAuth: () => ({
    isReady: true,
  }),
}))

vi.mock('@/features/auth/components/login-form', () => ({
  LoginForm: () => createElement('div', { 'data-testid': 'login-form-stub' }),
}))

afterEach(() => {
  cleanup()
  onNavigate.mockReset()
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
})
