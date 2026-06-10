// @vitest-environment jsdom

import { renderHook, waitFor } from '@testing-library/react'
import { QueryClientProvider } from '@tanstack/react-query'
import { createElement } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { createTestQueryClient } from '@/test-utils'

import { signalsQueryKeys } from './api'
import { useResolveSignalMutation } from './hooks'

const resolveSignal = vi.fn(async () => ({ id: 'signal-1', status: 'resolved' }))

vi.mock('./api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('./api')>()
  return {
    ...actual,
    resolveSignal: (...args: unknown[]) => resolveSignal(...args),
  }
})

describe('useResolveSignalMutation', () => {
  beforeEach(() => {
    resolveSignal.mockClear()
  })

  it('invalidates signal queries on success', async () => {
    const queryClient = createTestQueryClient()
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

    const { result } = renderHook(() => useResolveSignalMutation('est-1', 'signal-1'), {
      wrapper: ({ children }) =>
        createElement(QueryClientProvider, { client: queryClient }, children),
    })

    result.current.mutate()

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    expect(resolveSignal).toHaveBeenCalledWith('est-1', 'signal-1')
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: signalsQueryKeys.all })
  })
})
