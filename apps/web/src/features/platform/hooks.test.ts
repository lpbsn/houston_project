// @vitest-environment jsdom

import { QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import { createElement, type ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { createTestQueryClient } from '@/test-utils'

import { platformQueryKeys } from './api'
import {
  usePlatformEstablishmentsQuery,
  usePlatformMembershipsQuery,
  usePlatformOnboardingsQuery,
} from './hooks'

const listOnboardings = vi.fn()
const listEstablishments = vi.fn()
const listMemberships = vi.fn()

vi.mock('./api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('./api')>()
  return {
    ...actual,
    listPlatformOnboardings: (...args: unknown[]) => listOnboardings(...args),
    listPlatformEstablishments: (...args: unknown[]) => listEstablishments(...args),
    listPlatformMemberships: (...args: unknown[]) => listMemberships(...args),
  }
})

function wrapper() {
  const queryClient = createTestQueryClient()
  return {
    queryClient,
    Wrapper: ({ children }: { children: ReactNode }) =>
      createElement(QueryClientProvider, { client: queryClient }, children),
  }
}

describe('platform infinite queries', () => {
  beforeEach(() => {
    listOnboardings.mockReset()
    listEstablishments.mockReset()
    listMemberships.mockReset()
  })

  it('loads the first page then requests the next cursor', async () => {
    listOnboardings
      .mockResolvedValueOnce({ next_cursor: 'c2', results: [{ id: '1' }] })
      .mockResolvedValueOnce({ next_cursor: null, results: [{ id: '2' }] })
    const { Wrapper } = wrapper()
    const { result } = renderHook(() => usePlatformOnboardingsQuery('acme'), {
      wrapper: Wrapper,
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(listOnboardings).toHaveBeenCalledWith('acme', undefined)
    expect(result.current.hasNextPage).toBe(true)

    await result.current.fetchNextPage()
    await waitFor(() => expect(listOnboardings).toHaveBeenCalledWith('acme', 'c2'))
  })

  it('keeps global and relational establishment caches apart', async () => {
    listEstablishments.mockImplementation(async (_q: string, options: { organization_id?: string }) => ({
      next_cursor: options.organization_id ? 'rel-next' : null,
      results: [{ id: options.organization_id ? 'rel' : 'global' }],
    }))
    const { queryClient, Wrapper } = wrapper()
    const global = renderHook(() => usePlatformEstablishmentsQuery(''), { wrapper: Wrapper })
    const relational = renderHook(() => usePlatformEstablishmentsQuery('', 'org-1'), {
      wrapper: Wrapper,
    })

    await waitFor(() => expect(global.result.current.isSuccess).toBe(true))
    await waitFor(() => expect(relational.result.current.isSuccess).toBe(true))

    expect(platformQueryKeys.establishments('', '')).not.toEqual(
      platformQueryKeys.establishments('', 'org-1'),
    )
    expect(queryClient.getQueryData(platformQueryKeys.establishments('', ''))).not.toEqual(
      queryClient.getQueryData(platformQueryKeys.establishments('', 'org-1')),
    )
    expect(listEstablishments).toHaveBeenCalledWith('', {
      cursor: undefined,
      organization_id: undefined,
    })
    expect(listEstablishments).toHaveBeenCalledWith('', {
      cursor: undefined,
      organization_id: 'org-1',
    })

    await relational.result.current.fetchNextPage()
    await waitFor(() =>
      expect(listEstablishments).toHaveBeenCalledWith('', {
        cursor: 'rel-next',
        organization_id: 'org-1',
      }),
    )
  })

  it('passes membership relation filters and cursor', async () => {
    listMemberships
      .mockResolvedValueOnce({ next_cursor: 'm2', results: [] })
      .mockResolvedValueOnce({ next_cursor: null, results: [] })
    const filters = { user_id: 'user-1' }
    const { Wrapper } = wrapper()
    const { result } = renderHook(() => usePlatformMembershipsQuery(filters), {
      wrapper: Wrapper,
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(listMemberships).toHaveBeenCalledWith(filters, undefined)
    await result.current.fetchNextPage()
    await waitFor(() => expect(listMemberships).toHaveBeenCalledWith(filters, 'm2'))
  })
})
