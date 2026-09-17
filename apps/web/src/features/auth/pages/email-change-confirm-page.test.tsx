// @vitest-environment jsdom

import { createElement, type ReactNode } from 'react'
import { cleanup, render } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { AppRouteProvider } from '@/app/app-routes'
import { createMemoryHistory } from '@/app/app-history'

const confirmEmailChange = vi.hoisted(() => vi.fn())
const fetchBootstrap = vi.hoisted(() => vi.fn())
const authState = vi.hoisted(() => ({
  isAuthenticated: false,
  isReady: true,
}))

vi.mock('@/features/auth/api', () => ({
  AuthApiError: class AuthApiError extends Error {
    status: number
    code: string | null
    constructor(message: string, status: number, code: string | null = null) {
      super(message)
      this.name = 'AuthApiError'
      this.status = status
      this.code = code
    }
  },
  confirmEmailChange: (...args: unknown[]) => confirmEmailChange(...args),
  fetchBootstrap: (...args: unknown[]) => fetchBootstrap(...args),
}))

vi.mock('@/app/auth-provider', () => ({
  useAuth: () => ({
    isAuthenticated: authState.isAuthenticated,
    isReady: authState.isReady,
  }),
}))

import { EmailChangeConfirmPage } from './email-change-confirm-page'

function renderPage(initialHref: string) {
  const history = createMemoryHistory(initialHref)
  function Wrapper({ children }: { children: ReactNode }) {
    return createElement(AppRouteProvider, { history }, children)
  }
  const view = render(createElement(EmailChangeConfirmPage), { wrapper: Wrapper })
  return { history, ...view }
}

afterEach(() => {
  cleanup()
})

beforeEach(() => {
  confirmEmailChange.mockReset()
  fetchBootstrap.mockReset()
  confirmEmailChange.mockResolvedValue({ email: 'next@example.com' })
  authState.isAuthenticated = false
  authState.isReady = true
})

describe('EmailChangeConfirmPage', () => {
  it('moves the fragment secret into the confirm body and strips it from the URL', async () => {
    const { history } = renderPage('/email-change#confirm-token')

    expect(history.getHref()).toBe('/email-change')
    await vi.waitFor(() => {
      expect(confirmEmailChange).toHaveBeenCalledWith('confirm-token')
    })
    expect(fetchBootstrap).not.toHaveBeenCalled()
  })

  it('waits for auth readiness before confirming a logged-in session', async () => {
    authState.isReady = false
    authState.isAuthenticated = false
    const { rerender } = renderPage('/email-change#confirm-token')

    expect(confirmEmailChange).not.toHaveBeenCalled()

    authState.isReady = true
    authState.isAuthenticated = true
    rerender(createElement(EmailChangeConfirmPage))

    await vi.waitFor(() => {
      expect(confirmEmailChange).toHaveBeenCalledWith('confirm-token')
    })
    await vi.waitFor(() => {
      expect(fetchBootstrap).toHaveBeenCalledTimes(1)
    })
  })
})
