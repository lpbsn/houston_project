// @vitest-environment jsdom

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import { createElement, type ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { fetchChatStatus } from './api'
import { useChatAvailability } from './hooks'
import type { ChatStatus } from './types'

const availableStatus: ChatStatus = {
  chat_enabled: true,
  can_access: true,
  can_create_dm: true,
  can_create_group: false,
  can_manage_settings: false,
}

vi.mock('./api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('./api')>()
  return {
    ...actual,
    fetchChatStatus: vi.fn(async () => availableStatus),
  }
})

const fetchChatStatusMock = vi.mocked(fetchChatStatus)

const defaultAvailabilityProps = {
  establishmentId: 'est-1',
  hasOperationalAccess: true,
  bootstrapChatAvailable: false,
}

function createAvailabilityTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        staleTime: 30_000,
        refetchOnWindowFocus: false,
      },
      mutations: { retry: false },
    },
  })
}

function createWrapper(queryClient: QueryClient) {
  return ({ children }: { children: ReactNode }) =>
    createElement(QueryClientProvider, { client: queryClient }, children)
}

describe('useChatAvailability', () => {
  beforeEach(() => {
    fetchChatStatusMock.mockClear()
  })

  it('does not invalidate chat status on mount or simple rerender', async () => {
    const queryClient = createAvailabilityTestQueryClient()
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

    const { rerender } = renderHook(() => useChatAvailability(defaultAvailabilityProps), {
      wrapper: createWrapper(queryClient),
    })

    await waitFor(() => {
      expect(fetchChatStatusMock).toHaveBeenCalledTimes(1)
    })

    invalidateSpy.mockClear()
    rerender()

    expect(invalidateSpy).not.toHaveBeenCalled()
  })

  it('does not refetch chat status on rerender while data is fresh', async () => {
    const queryClient = createAvailabilityTestQueryClient()

    const { rerender } = renderHook(() => useChatAvailability(defaultAvailabilityProps), {
      wrapper: createWrapper(queryClient),
    })

    await waitFor(() => {
      expect(fetchChatStatusMock).toHaveBeenCalledTimes(1)
    })

    rerender()

    await waitFor(() => {
      expect(fetchChatStatusMock).toHaveBeenCalledTimes(1)
    })
  })
})
