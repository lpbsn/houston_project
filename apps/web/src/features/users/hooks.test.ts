// @vitest-environment jsdom

import { createElement, type ReactNode } from 'react'
import { QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { createTestQueryClient } from '@/test-utils'

const searchEstablishmentUsers = vi.fn()

vi.mock('@/features/users/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/features/users/api')>()
  return {
    ...actual,
    searchEstablishmentUsers: (...args: unknown[]) => searchEstablishmentUsers(...args),
  }
})

import { useEstablishmentUserSearchQuery } from './hooks'

function wrapper({ children }: { children: ReactNode }) {
  return createElement(QueryClientProvider, { client: createTestQueryClient() }, children)
}

describe('useEstablishmentUserSearchQuery', () => {
  beforeEach(() => {
    searchEstablishmentUsers.mockReset()
    searchEstablishmentUsers.mockResolvedValue([])
  })

  it('does not fetch an empty query even when businessUnitId is set', () => {
    renderHook(
      () => useEstablishmentUserSearchQuery('est-1', '', { businessUnitId: 'bu-1' }),
      { wrapper },
    )

    expect(searchEstablishmentUsers).not.toHaveBeenCalled()
  })

  it('fetches an empty query only when allowEmptyQuery and businessUnitId are set', async () => {
    renderHook(
      () =>
        useEstablishmentUserSearchQuery('est-1', '', {
          businessUnitId: 'bu-1',
          allowEmptyQuery: true,
        }),
      { wrapper },
    )

    await waitFor(() => {
      expect(searchEstablishmentUsers).toHaveBeenCalledWith('est-1', '', {
        businessUnitId: 'bu-1',
      })
    })
  })

  it('does not fetch a one-character query even with allowEmptyQuery', () => {
    renderHook(
      () =>
        useEstablishmentUserSearchQuery('est-1', 'a', {
          businessUnitId: 'bu-1',
          allowEmptyQuery: true,
        }),
      { wrapper },
    )

    expect(searchEstablishmentUsers).not.toHaveBeenCalled()
  })

  it('does not fetch an empty query with allowEmptyQuery when businessUnitId is missing', () => {
    renderHook(
      () => useEstablishmentUserSearchQuery('est-1', '', { allowEmptyQuery: true }),
      { wrapper },
    )

    expect(searchEstablishmentUsers).not.toHaveBeenCalled()
  })
})
