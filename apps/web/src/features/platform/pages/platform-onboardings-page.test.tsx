// @vitest-environment jsdom

import { QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { createElement, type ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { createTestQueryClient } from '@/test-utils'

import { PlatformOnboardingsPage } from './platform-onboardings-page'

const listOnboardings = vi.fn()
const startOnboarding = vi.fn()
const routeState = vi.hoisted(() => ({
  search: '',
  navigate: vi.fn(),
}))

vi.mock('@/app/app-routes', () => ({
  useAppRoute: () => ({
    search: routeState.search,
    navigate: routeState.navigate,
  }),
}))

vi.mock('@/features/platform/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/features/platform/api')>()
  return {
    ...actual,
    listPlatformOnboardings: (...args: unknown[]) => listOnboardings(...args),
    startPlatformOnboarding: (...args: unknown[]) => startOnboarding(...args),
  }
})

function renderPage() {
  const queryClient = createTestQueryClient()
  const wrap = ({ children }: { children: ReactNode }) =>
    createElement(QueryClientProvider, { client: queryClient }, children)
  return render(createElement(PlatformOnboardingsPage), { wrapper: wrap })
}

function installDialogPolyfill() {
  if (typeof HTMLDialogElement === 'undefined') {
    return
  }
  HTMLDialogElement.prototype.showModal = function showModal() {
    this.setAttribute('open', '')
  }
  HTMLDialogElement.prototype.close = function close() {
    this.removeAttribute('open')
    this.dispatchEvent(new Event('close'))
  }
}

describe('PlatformOnboardingsPage', () => {
  afterEach(() => {
    cleanup()
  })

  beforeEach(() => {
    installDialogPolyfill()
    routeState.search = ''
    routeState.navigate.mockReset()
    listOnboardings.mockReset()
    startOnboarding.mockReset()
    listOnboardings.mockResolvedValue({ next_cursor: null, results: [] })
  })

  it('keeps creation behind a dialog and navigates after start', async () => {
    startOnboarding.mockResolvedValue({ id: 'sess-1' })
    renderPage()

    expect(screen.queryByRole('dialog')).toBeNull()
    expect(screen.queryByPlaceholderText('Nom de l’organisation')).toBeNull()

    fireEvent.click(screen.getByRole('button', { name: 'Nouvel onboarding' }))
    expect(await screen.findByRole('dialog')).toBeTruthy()

    fireEvent.change(screen.getByPlaceholderText('Nom de l’organisation'), {
      target: { value: 'Acme' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Démarrer' }))

    await waitFor(() => {
      expect(startOnboarding.mock.calls[0]?.[0]).toEqual({
        organization_name: 'Acme',
        establishment_name: null,
      })
    })
    await waitFor(() => {
      expect(routeState.navigate).toHaveBeenCalledWith('/platform/onboardings/sess-1')
    })
  })

  it('blocks dialog close while start is pending', async () => {
    startOnboarding.mockReturnValue(new Promise(() => undefined))
    renderPage()
    fireEvent.click(screen.getByRole('button', { name: 'Nouvel onboarding' }))
    fireEvent.change(await screen.findByPlaceholderText('Nom de l’organisation'), {
      target: { value: 'Acme' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Démarrer' }))

    await waitFor(() => {
      expect((screen.getByRole('button', { name: 'Annuler' }) as HTMLButtonElement).disabled).toBe(
        true,
      )
    })
    fireEvent.click(screen.getByRole('button', { name: 'Annuler' }))
    expect(screen.getByRole('dialog')).toBeTruthy()
  })

  it('uses resource links instead of row clicks and shows load more for next_cursor', async () => {
    listOnboardings.mockResolvedValue({
      next_cursor: 'next',
      results: [
        {
          id: 'sess-1',
          organization_name: 'Acme',
          establishment_name: 'HQ',
          functional_status: 'in_progress',
        },
      ],
    })
    renderPage()

    const resource = await screen.findByRole('link', { name: 'Acme' })
    expect(resource.getAttribute('href')).toBe('/platform/onboardings/sess-1')
    expect(screen.getByRole('button', { name: 'Charger plus' })).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Acme' })).toBeNull()
  })

  it('distinguishes empty from no search results and retries errors', async () => {
    listOnboardings.mockRejectedValueOnce(new Error('boom'))
    renderPage()
    expect(await screen.findByTestId('platform-error')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Réessayer' }))
    await waitFor(() => expect(listOnboardings).toHaveBeenCalledTimes(2))

    cleanup()
    listOnboardings.mockResolvedValue({ next_cursor: null, results: [] })
    renderPage()
    expect(await screen.findByTestId('platform-empty')).toBeTruthy()

    cleanup()
    routeState.search = '?q=zzz'
    renderPage()
    expect(await screen.findByTestId('platform-no-results')).toBeTruthy()
  })
})
