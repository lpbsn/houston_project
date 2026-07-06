// @vitest-environment jsdom

import { renderHook, waitFor } from '@testing-library/react'
import { QueryClientProvider } from '@tanstack/react-query'
import { createElement } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { createTestQueryClient } from '@/test-utils'

import { useCreateActionPlanMutation } from './hooks'

const createActionPlan = vi.fn(async () => ({
  id: 'exec-1',
  status: 'in_progress',
  action_plan_id: 'plan-1',
}))

vi.mock('./api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('./api')>()
  return {
    ...actual,
    createActionPlan: (...args: unknown[]) => createActionPlan(...args),
  }
})

describe('useCreateActionPlanMutation', () => {
  beforeEach(() => {
    createActionPlan.mockClear()
  })

  it('invalidates execution and signal queries when create returns an execution', async () => {
    const queryClient = createTestQueryClient()
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

    const { result } = renderHook(() => useCreateActionPlanMutation('est-1'), {
      wrapper: ({ children }) =>
        createElement(QueryClientProvider, { client: queryClient }, children),
    })

    result.current.mutate({
      title: 'Linked plan',
      pilot_business_unit_id: 'bu-1',
      source_signal_id: 'sig-1',
      tasks: [],
      assignees: [],
    })

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ['action-plans', 'action-plan-execution-feed', 'est-1'],
    })
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ['action-plans', 'execution-detail', 'est-1', 'exec-1'],
    })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['signals', 'feed', 'est-1'] })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['signals', 'detail', 'est-1'] })
  })
})
