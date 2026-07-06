// @vitest-environment jsdom

import { renderHook, waitFor } from '@testing-library/react'
import { QueryClientProvider } from '@tanstack/react-query'
import { createElement } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { createTestQueryClient } from '@/test-utils'

import { useCreateActionPlanMutation, useCreateActionPlanScheduleMutation } from './hooks'

const createActionPlan = vi.fn(async () => ({
  id: 'exec-1',
  status: 'in_progress',
  action_plan_id: 'plan-1',
}))

const createActionPlanSchedule = vi.fn(async () => ({
  id: 'schedule-1',
  action_plan_id: 'plan-1',
}))

vi.mock('./api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('./api')>()
  return {
    ...actual,
    createActionPlan: (...args: unknown[]) => createActionPlan(...args),
    createActionPlanSchedule: (...args: unknown[]) => createActionPlanSchedule(...args),
  }
})

describe('useCreateActionPlanMutation', () => {
  beforeEach(() => {
    createActionPlan.mockClear()
    createActionPlanSchedule.mockClear()
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

describe('useCreateActionPlanScheduleMutation', () => {
  beforeEach(() => {
    createActionPlanSchedule.mockClear()
  })

  it('invalidates catalog and schedule queries after schedule create', async () => {
    const queryClient = createTestQueryClient()
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

    const { result } = renderHook(() => useCreateActionPlanScheduleMutation('est-1', 'plan-1'), {
      wrapper: ({ children }) =>
        createElement(QueryClientProvider, { client: queryClient }, children),
    })

    result.current.mutate({
      end_date: '2026-12-31',
      start_at: '09:00:00',
      end_at: '10:00:00',
      recurrence_days: ['monday'],
    })

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ['action-plans', 'catalog', 'est-1'],
    })
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ['action-plans', 'detail', 'est-1', 'plan-1'],
    })
  })
})
