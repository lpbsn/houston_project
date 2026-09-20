// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { createElement } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { PlatformShell } from './platform-shell'

const navigate = vi.fn()

vi.mock('@/app/app-routes', () => ({
  useAppRoute: () => ({ navigate }),
}))

vi.mock('@/app/auth-provider', () => ({
  useAuth: () => ({
    user: { first_name: 'Ada', last_name: 'Lovelace', email: 'ada@example.com' },
  }),
}))

vi.mock('@/features/auth/api', () => ({
  clearAuthState: vi.fn(),
}))

describe('PlatformShell', () => {
  afterEach(() => {
    cleanup()
    navigate.mockReset()
  })

  it('marks the current section with aria-current on a real link', () => {
    render(createElement(PlatformShell, { section: 'organizations', children: 'content' }))
    const current = screen.getByRole('link', { name: 'Organisations' })
    expect(current.getAttribute('aria-current')).toBe('page')
    expect(current.getAttribute('href')).toBe('/platform/organizations')
    expect(screen.getByRole('link', { name: 'Onboardings' }).getAttribute('aria-current')).toBeNull()
  })

  it('navigates on unmodified left click and leaves modified clicks to the browser', () => {
    render(createElement(PlatformShell, { section: 'onboardings', children: 'content' }))
    const users = screen.getByRole('link', { name: 'Utilisateurs' })

    fireEvent.click(users, { button: 0, metaKey: true })
    expect(navigate).not.toHaveBeenCalled()

    fireEvent.click(users, { button: 0 })
    expect(navigate).toHaveBeenCalledWith('/platform/users')
  })
})
