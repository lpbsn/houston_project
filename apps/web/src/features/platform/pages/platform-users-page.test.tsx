// @vitest-environment jsdom

import { QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen } from '@testing-library/react'
import { createElement, type ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { createTestQueryClient } from '@/test-utils'

import { PlatformUsersPage } from './platform-users-page'

const getUser = vi.fn()
const listMemberships = vi.fn()
const routeState = vi.hoisted(() => ({
  search: '?q=ada',
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
    getPlatformUser: (...args: unknown[]) => getUser(...args),
    listPlatformMemberships: (...args: unknown[]) => listMemberships(...args),
  }
})

describe('PlatformUsersPage detail relations', () => {
  afterEach(() => {
    cleanup()
  })

  beforeEach(() => {
    getUser.mockReset()
    listMemberships.mockReset()
  })

  it('links membership organization and establishment without copying the users search', async () => {
    getUser.mockResolvedValue({
      id: 'user-1',
      display_name: 'Ada Lovelace',
      email: 'ada@example.com',
      status: 'active',
      first_name: 'Ada',
      last_name: 'Lovelace',
      created_at: '2026-01-01T00:00:00.000Z',
      updated_at: '2026-01-01T00:00:00.000Z',
    })
    listMemberships.mockResolvedValue({
      next_cursor: 'm2',
      results: [
        {
          id: 'mem-1',
          user_id: 'user-1',
          user_display_name: 'Ada Lovelace',
          user_email: 'ada@example.com',
          organization_id: 'org-1',
          organization_name: 'Acme',
          establishment_id: 'est-1',
          establishment_name: 'HQ',
          role: 'owner',
          status: 'active',
        },
      ],
    })
    const queryClient = createTestQueryClient()
    const wrap = ({ children }: { children: ReactNode }) =>
      createElement(QueryClientProvider, { client: queryClient }, children)
    render(createElement(PlatformUsersPage, { resourceId: 'user-1' }), { wrapper: wrap })

    expect((await screen.findByRole('link', { name: 'Acme' })).getAttribute('href')).toBe(
      '/platform/organizations/org-1',
    )
    expect(screen.getByRole('link', { name: 'HQ' }).getAttribute('href')).toBe(
      '/platform/establishments/est-1',
    )
    expect(screen.getByRole('link', { name: 'Utilisateurs' }).getAttribute('href')).toBe(
      '/platform/users?q=ada',
    )
    expect(screen.getByRole('button', { name: 'Charger plus' })).toBeTruthy()
    expect(listMemberships).toHaveBeenCalledWith({ user_id: 'user-1' }, undefined)
  })
})
