// @vitest-environment jsdom

import { QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen } from '@testing-library/react'
import { createElement, type ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { createTestQueryClient } from '@/test-utils'

import { PlatformEstablishmentsPage } from './platform-establishments-page'

const listEstablishments = vi.fn()
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
    listPlatformEstablishments: (...args: unknown[]) => listEstablishments(...args),
  }
})

function renderList() {
  const queryClient = createTestQueryClient()
  const wrap = ({ children }: { children: ReactNode }) =>
    createElement(QueryClientProvider, { client: queryClient }, children)
  return render(createElement(PlatformEstablishmentsPage), { wrapper: wrap })
}

describe('PlatformEstablishmentsPage list', () => {
  afterEach(() => {
    cleanup()
  })

  beforeEach(() => {
    routeState.search = '?q=hq'
    routeState.navigate.mockReset()
    listEstablishments.mockReset()
  })

  it('shows business status and preserves q on resource links', async () => {
    listEstablishments.mockResolvedValue({
      next_cursor: null,
      results: [
        {
          id: 'est-1',
          name: 'HQ',
          status: 'draft',
          organization_name: 'Acme',
          onboarding: { functional_status: 'error' },
        },
      ],
    })
    renderList()

    expect(await screen.findByText('Brouillon')).toBeTruthy()
    expect(screen.queryByText('Erreur')).toBeNull()
    expect(screen.getByRole('link', { name: 'HQ' }).getAttribute('href')).toBe(
      '/platform/establishments/est-1?q=hq',
    )
  })
})
