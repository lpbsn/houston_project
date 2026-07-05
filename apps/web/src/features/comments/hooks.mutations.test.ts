// @vitest-environment jsdom

import { renderHook, waitFor } from '@testing-library/react'
import { QueryClientProvider } from '@tanstack/react-query'
import { createElement } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { createTestQueryClient } from '@/test-utils'

import { commentsQueryKeys } from './api'
import {
  useCreateExecutionCommentMutation,
  useCreateSignalCommentMutation,
  useResolveExecutionCommentMutation,
  useUnresolveExecutionCommentMutation,
} from './hooks'

const createSignalComment = vi.fn(async () => ({
  id: 'comment-1',
  origin: 'signal' as const,
  body: 'hello',
  author: { membership_id: 'm-1', display_name: 'Alice' },
  mentions: [],
  created_at: '2026-06-15T10:30:00Z',
}))

const createExecutionComment = vi.fn(async () => ({
  id: 'comment-3',
  origin: 'action_plan_execution' as const,
  body: 'hello execution',
  author: { membership_id: 'm-1', display_name: 'Alice' },
  mentions: [],
  created_at: '2026-06-15T10:40:00Z',
}))

const resolveExecutionComment = vi.fn(async () => ({
  item_type: 'execution_thread' as const,
  id: 'comment-3',
  origin: 'action_plan_execution' as const,
  body: 'root execution',
  author: { membership_id: 'm-1', display_name: 'Alice' },
  mentions: [],
  created_at: '2026-06-15T10:30:00Z',
  replies: [],
  is_resolved: true,
  resolved_at: '2026-06-15T11:00:00Z',
  resolved_by: { membership_id: 'm-1', display_name: 'Alice' },
  permission_hints: { can_reply: true, can_resolve: true },
}))

const unresolveExecutionComment = vi.fn(async () => ({
  item_type: 'execution_thread' as const,
  id: 'comment-3',
  origin: 'action_plan_execution' as const,
  body: 'root execution',
  author: { membership_id: 'm-1', display_name: 'Alice' },
  mentions: [],
  created_at: '2026-06-15T10:30:00Z',
  replies: [],
  is_resolved: false,
  resolved_at: null,
  resolved_by: null,
  permission_hints: { can_reply: true, can_resolve: true },
}))

vi.mock('./api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('./api')>()
  return {
    ...actual,
    createSignalComment: (...args: unknown[]) => createSignalComment(...args),
    createExecutionComment: (...args: unknown[]) => createExecutionComment(...args),
    resolveExecutionComment: (...args: unknown[]) => resolveExecutionComment(...args),
    unresolveExecutionComment: (...args: unknown[]) => unresolveExecutionComment(...args),
  }
})

describe('comment mutations', () => {
  beforeEach(() => {
    createSignalComment.mockClear()
    createExecutionComment.mockClear()
    resolveExecutionComment.mockClear()
    unresolveExecutionComment.mockClear()
  })

  it('invalidates signal comment queries on success', async () => {
    const queryClient = createTestQueryClient()
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

    const { result } = renderHook(() => useCreateSignalCommentMutation('est-1', 'signal-1'), {
      wrapper: ({ children }) =>
        createElement(QueryClientProvider, { client: queryClient }, children),
    })

    result.current.mutate({ body: 'hello', mentioned_membership_ids: [] })

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: commentsQueryKeys.signalList('est-1', 'signal-1'),
    })
  })

  it('invalidates execution comment queries after create', async () => {
    const queryClient = createTestQueryClient()
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

    const { result } = renderHook(() => useCreateExecutionCommentMutation('est-1', 'exec-1'), {
      wrapper: ({ children }) =>
        createElement(QueryClientProvider, { client: queryClient }, children),
    })

    result.current.mutate({ body: 'hello execution', mentioned_membership_ids: [] })

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: commentsQueryKeys.executionList('est-1', 'exec-1'),
    })
  })

  it('invalidates execution comment queries after resolve', async () => {
    const queryClient = createTestQueryClient()
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

    const { result } = renderHook(() => useResolveExecutionCommentMutation('est-1', 'exec-1'), {
      wrapper: ({ children }) =>
        createElement(QueryClientProvider, { client: queryClient }, children),
    })

    result.current.mutate('comment-3')

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: commentsQueryKeys.executionList('est-1', 'exec-1'),
    })
  })

  it('invalidates execution comment queries after unresolve', async () => {
    const queryClient = createTestQueryClient()
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

    const { result } = renderHook(() => useUnresolveExecutionCommentMutation('est-1', 'exec-1'), {
      wrapper: ({ children }) =>
        createElement(QueryClientProvider, { client: queryClient }, children),
    })

    result.current.mutate('comment-3')

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: commentsQueryKeys.executionList('est-1', 'exec-1'),
    })
  })
})
