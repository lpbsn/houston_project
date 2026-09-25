// @vitest-environment jsdom

import { renderHook, waitFor } from '@testing-library/react'
import { QueryClientProvider } from '@tanstack/react-query'
import { createElement } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { createTestQueryClient } from '@/test-utils'

import { actionPlansQueryKeys } from './api'
import {
  useActionPlanExecutionDetailQuery,
  useCreateActionPlanMutation,
  useDeleteActionPlanMutation,
  useMarkActionPlanTaskDoneMutation,
  useMarkActionPlanTaskPendingMutation,
  useUpdateActionPlanExecutionMutation,
} from './hooks'
import type { ActionPlanExecutionDetail, ActionPlanTaskExecution } from './types'

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

const fetchActionPlanExecutionDetail = vi.fn(() => new Promise(() => undefined))

const markActionPlanTaskDone = vi.fn()

const markActionPlanTaskPending = vi.fn()

vi.mock('./api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('./api')>()
  return {
    ...actual,
    createActionPlan: (...args: unknown[]) => createActionPlan(...args),
    updateActionPlanExecution: (...args: unknown[]) => updateActionPlanExecution(...args),
    deleteActionPlan: (...args: unknown[]) => deleteActionPlan(...args),
    fetchActionPlanExecutionDetail: (...args: unknown[]) =>
      fetchActionPlanExecutionDetail(...args),
    markActionPlanTaskDone: (...args: unknown[]) => markActionPlanTaskDone(...args),
    markActionPlanTaskPending: (...args: unknown[]) => markActionPlanTaskPending(...args),
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

const taskPermissionHints = {
  can_mark_done: true,
  can_unmark_done: false,
  can_skip: true,
  can_create_observation: true,
}

function buildCachedTask(overrides: Partial<ActionPlanTaskExecution> = {}): ActionPlanTaskExecution {
  return {
    id: 'task-1',
    task: 'Contrôler la terrasse',
    description: '',
    deadline_at: null,
    assigned_membership_id: null,
    assigned_display_name: null,
    position: 1,
    status: 'pending',
    business_unit: {
      id: 'bu-1',
      specific_name: 'Restaurant',
      instance_description: '',
      active: true,
      generic: {
        key: 'restaurant',
        label: 'Restaurant',
        description: '',
        unit_type: 'dedicated',
      },
    },
    observation_id: null,
    skipped_reason: null,
    completed_at: null,
    skipped_at: null,
    observation_created_at: null,
    permission_hints: taskPermissionHints,
    ...overrides,
  }
}

function buildCachedExecution(
  task: ActionPlanTaskExecution = buildCachedTask(),
): ActionPlanExecutionDetail {
  return {
    id: 'exec-1',
    task_executions: [task],
  } as ActionPlanExecutionDetail
}

function renderTaskMutation(
  queryClient: ReturnType<typeof createTestQueryClient>,
  hook: typeof useMarkActionPlanTaskDoneMutation | typeof useMarkActionPlanTaskPendingMutation,
) {
  return renderHook(
    () => {
      const detail = useActionPlanExecutionDetailQuery('est-1', 'exec-1')
      const mutation = hook('est-1', 'exec-1')
      return { detail, mutation }
    },
    {
      wrapper: ({ children }) =>
        createElement(QueryClientProvider, { client: queryClient }, children),
    },
  )
}

describe('task status mutations', () => {
  beforeEach(() => {
    markActionPlanTaskDone.mockReset()
    markActionPlanTaskPending.mockReset()
    fetchActionPlanExecutionDetail.mockClear()
  })

  it('writes the returned task into the detail cache before the detail refetch settles', async () => {
    const queryClient = createTestQueryClient()
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')
    queryClient.setQueryData(
      actionPlansQueryKeys.executionDetail('est-1', 'exec-1'),
      buildCachedExecution(),
    )
    const doneTask = buildCachedTask({
      status: 'done',
      completed_at: '2026-09-25T08:00:00Z',
      permission_hints: {
        ...taskPermissionHints,
        can_mark_done: false,
        can_unmark_done: true,
      },
    })
    markActionPlanTaskDone.mockResolvedValue(doneTask)

    const { result } = renderTaskMutation(queryClient, useMarkActionPlanTaskDoneMutation)
    await result.current.mutation.mutateAsync('task-1')

    const cached = queryClient.getQueryData<ActionPlanExecutionDetail>(
      actionPlansQueryKeys.executionDetail('est-1', 'exec-1'),
    )
    expect(cached?.task_executions[0]).toEqual(doneTask)
    expect(fetchActionPlanExecutionDetail).toHaveBeenCalled()
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ['action-plans', 'action-plan-execution-feed', 'est-1'],
    })
  })

  it('writes a mark-pending task into the detail cache before the detail refetch settles', async () => {
    const queryClient = createTestQueryClient()
    queryClient.setQueryData(
      actionPlansQueryKeys.executionDetail('est-1', 'exec-1'),
      buildCachedExecution(
        buildCachedTask({
          status: 'done',
          permission_hints: {
            ...taskPermissionHints,
            can_mark_done: false,
            can_unmark_done: true,
          },
        }),
      ),
    )
    const pendingTask = buildCachedTask({ status: 'pending', completed_at: null })
    markActionPlanTaskPending.mockResolvedValue(pendingTask)

    const { result } = renderTaskMutation(queryClient, useMarkActionPlanTaskPendingMutation)
    await result.current.mutation.mutateAsync('task-1')

    const cached = queryClient.getQueryData<ActionPlanExecutionDetail>(
      actionPlansQueryKeys.executionDetail('est-1', 'exec-1'),
    )
    expect(cached?.task_executions[0]).toEqual(pendingTask)
    expect(fetchActionPlanExecutionDetail).toHaveBeenCalled()
  })

  it('leaves the cached task unchanged when mark-done fails', async () => {
    const queryClient = createTestQueryClient()
    const pendingTask = buildCachedTask()
    queryClient.setQueryData(
      actionPlansQueryKeys.executionDetail('est-1', 'exec-1'),
      buildCachedExecution(pendingTask),
    )
    markActionPlanTaskDone.mockRejectedValue(new Error('network'))

    const { result } = renderTaskMutation(queryClient, useMarkActionPlanTaskDoneMutation)
    await expect(result.current.mutation.mutateAsync('task-1')).rejects.toThrow('network')

    const cached = queryClient.getQueryData<ActionPlanExecutionDetail>(
      actionPlansQueryKeys.executionDetail('est-1', 'exec-1'),
    )
    expect(cached?.task_executions[0]?.status).toBe('pending')
  })
})
