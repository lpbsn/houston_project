// @vitest-environment jsdom

import { renderHook, waitFor } from '@testing-library/react'
import { QueryClientProvider } from '@tanstack/react-query'
import { createElement } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { createTestQueryClient } from '@/test-utils'

import { useAcceptActionMutation, useReassignActionMutation } from './hooks'

const acceptAction = vi.fn(async () => ({ id: 'action-1', status: 'in_progress' }))
const reassignAction = vi.fn(async () => ({ id: 'action-1', status: 'open' }))

vi.mock('./api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('./api')>()
  return {
    ...actual,
    acceptAction: (...args: unknown[]) => acceptAction(...args),
    reassignAction: (...args: unknown[]) => reassignAction(...args),
  }
})

describe('useAcceptActionMutation', () => {
  beforeEach(() => {
    acceptAction.mockClear()
  })

  it('invalidates action and signal queries on success', async () => {
    const queryClient = createTestQueryClient()
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

    const { result } = renderHook(() => useAcceptActionMutation('est-1', 'action-1'), {
      wrapper: ({ children }) =>
        createElement(QueryClientProvider, { client: queryClient }, children),
    })

    result.current.mutate()

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    expect(acceptAction).toHaveBeenCalledWith('est-1', 'action-1')
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ['actions', 'execution-feed', 'est-1'],
    })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['actions', 'detail', 'est-1'] })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['signals', 'feed', 'est-1'] })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['signals', 'detail', 'est-1'] })
    expect(invalidateSpy).not.toHaveBeenCalledWith({ queryKey: ['actions'] })
    expect(invalidateSpy).not.toHaveBeenCalledWith({ queryKey: ['signals'] })
    expect(invalidateSpy).not.toHaveBeenCalledWith({ queryKey: ['auth'] })
  })
})

describe('useReassignActionMutation', () => {
  beforeEach(() => {
    reassignAction.mockClear()
  })

  it('calls reassign with assignee_ids and invalidates targeted queries', async () => {
    const queryClient = createTestQueryClient()
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

    const { result } = renderHook(() => useReassignActionMutation('est-1'), {
      wrapper: ({ children }) =>
        createElement(QueryClientProvider, { client: queryClient }, children),
    })

    result.current.mutate({
      actionId: 'action-1',
      assigneeIds: ['member-1', 'member-2'],
    })

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    expect(reassignAction).toHaveBeenCalledWith('est-1', 'action-1', ['member-1', 'member-2'])
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ['actions', 'execution-feed', 'est-1'],
    })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['actions', 'detail', 'est-1'] })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['signals', 'feed', 'est-1'] })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['signals', 'detail', 'est-1'] })
    expect(invalidateSpy).not.toHaveBeenCalledWith({ queryKey: ['actions'] })
    expect(invalidateSpy).not.toHaveBeenCalledWith({ queryKey: ['auth'] })
  })
})
