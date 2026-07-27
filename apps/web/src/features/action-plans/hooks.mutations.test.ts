// @vitest-environment jsdom

import { renderHook, waitFor } from '@testing-library/react'
import { QueryClientProvider } from '@tanstack/react-query'
import { createElement } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { createTestQueryClient } from '@/test-utils'

import {
  useCreateActionPlanMutation,
  useDeleteActionPlanMutation,
  useUpdateActionPlanExecutionMutation,
} from './hooks'

const createActionPlan = vi.fn(async () => ({
  id: 'exec-1',
  status: 'in_progress',
  action_plan_id: 'plan-1',
}))

const updateActionPlanExecution = vi.fn(async () => ({
  id: 'exec-1',
  status: 'in_progress',
  action_plan_id: 'plan-1',
}))

const deleteActionPlan = vi.fn(async () => undefined)

vi.mock('./api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('./api')>()
  return {
    ...actual,
    createActionPlan: (...args: unknown[]) => createActionPlan(...args),
    updateActionPlanExecution: (...args: unknown[]) => updateActionPlanExecution(...args),
    deleteActionPlan: (...args: unknown[]) => deleteActionPlan(...args),
  }
})

describe('useCreateActionPlanMutation', () => {
  beforeEach(() => {
    createActionPlan.mockClear()
    updateActionPlanExecution.mockClear()
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

  it('invalidates execution feed surfaces when create returns atomic planning response', async () => {
    createActionPlan.mockResolvedValueOnce({
      replayed: false,
      action_plan_id: 'plan-direct-1',
      summary: { executions_created: 2, schedules_created: 1 },
      executions: [
        {
          item_id: 'i1',
          id: 'exec-a',
          primary_membership_id: 'm1',
          status: 'scheduled',
        },
      ],
      schedules: [],
    })

    const queryClient = createTestQueryClient()
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

    const { result } = renderHook(() => useCreateActionPlanMutation('est-1'), {
      wrapper: ({ children }) =>
        createElement(QueryClientProvider, { client: queryClient }, children),
    })

    result.current.mutate({
      title: 'Direct planning',
      pilot_business_unit_id: 'bu-1',
      submission_id: 'sub-1',
      use_shared_chronology: false,
      items: [],
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
      queryKey: ['action-plans', 'action-plan-execution-upcoming', 'est-1'],
    })
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ['action-plans', 'catalog', 'est-1'],
    })
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ['action-plans', 'detail', 'est-1', 'plan-direct-1'],
    })
  })
})

describe('useDeleteActionPlanMutation', () => {
  beforeEach(() => {
    deleteActionPlan.mockClear()
  })

  it('invalidates catalog and detail queries after delete', async () => {
    const queryClient = createTestQueryClient()
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

    const { result } = renderHook(() => useDeleteActionPlanMutation('est-1', 'plan-1'), {
      wrapper: ({ children }) =>
        createElement(QueryClientProvider, { client: queryClient }, children),
    })

    result.current.mutate()

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    expect(deleteActionPlan).toHaveBeenCalledWith('est-1', 'plan-1')
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ['action-plans', 'catalog', 'est-1'],
    })
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ['action-plans', 'detail', 'est-1', 'plan-1'],
    })
  })
})

describe('useUpdateActionPlanExecutionMutation', () => {
  beforeEach(() => {
    updateActionPlanExecution.mockClear()
  })

  it('invalidates execution detail and feeds after update', async () => {
    const queryClient = createTestQueryClient()
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

    const { result } = renderHook(
      () => useUpdateActionPlanExecutionMutation('est-1', 'exec-1'),
      {
        wrapper: ({ children }) =>
          createElement(QueryClientProvider, { client: queryClient }, children),
      },
    )

    result.current.mutate({
      expected_updated_at: '2026-07-01T09:00:00.000Z',
      title: 'Updated',
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
  })
})
