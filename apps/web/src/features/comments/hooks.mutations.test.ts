// @vitest-environment jsdom

import { renderHook, waitFor } from '@testing-library/react'
import { QueryClientProvider } from '@tanstack/react-query'
import { createElement } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { createTestQueryClient } from '@/test-utils'

import { commentsQueryKeys } from './api'
import {
  useCreateActionCommentMutation,
  useCreateSignalCommentMutation,
  useResolveActionCommentMutation,
  useUnresolveActionCommentMutation,
} from './hooks'

const createSignalComment = vi.fn(async () => ({
  id: 'comment-1',
  origin: 'signal' as const,
  body: 'hello',
  author: { membership_id: 'm-1', display_name: 'Alice' },
  mentions: [],
  created_at: '2026-06-15T10:30:00Z',
}))

const createActionComment = vi.fn(async () => ({
  id: 'comment-2',
  origin: 'action' as const,
  body: 'reply',
  author: { membership_id: 'm-1', display_name: 'Alice' },
  mentions: [],
  created_at: '2026-06-15T10:35:00Z',
}))

const resolveActionComment = vi.fn(async () => ({
  item_type: 'action_thread' as const,
  id: 'comment-2',
  origin: 'action' as const,
  body: 'root',
  author: { membership_id: 'm-1', display_name: 'Alice' },
  mentions: [],
  created_at: '2026-06-15T10:30:00Z',
  replies: [],
  is_resolved: true,
  resolved_at: '2026-06-15T11:00:00Z',
  resolved_by: { membership_id: 'm-1', display_name: 'Alice' },
  permission_hints: { can_reply: true, can_resolve: true },
}))

const unresolveActionComment = vi.fn(async () => ({
  item_type: 'action_thread' as const,
  id: 'comment-2',
  origin: 'action' as const,
  body: 'root',
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
    createActionComment: (...args: unknown[]) => createActionComment(...args),
    resolveActionComment: (...args: unknown[]) => resolveActionComment(...args),
    unresolveActionComment: (...args: unknown[]) => unresolveActionComment(...args),
  }
})

describe('comment mutations', () => {
  beforeEach(() => {
    createSignalComment.mockClear()
    createActionComment.mockClear()
    resolveActionComment.mockClear()
    unresolveActionComment.mockClear()
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

  it('invalidates action comment queries after reply', async () => {
    const queryClient = createTestQueryClient()
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

    const { result } = renderHook(() => useCreateActionCommentMutation('est-1', 'action-1'), {
      wrapper: ({ children }) =>
        createElement(QueryClientProvider, { client: queryClient }, children),
    })

    result.current.mutate({
      body: 'reply',
      mentioned_membership_ids: [],
      parent_comment_id: 'root-1',
    })

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: commentsQueryKeys.actionList('est-1', 'action-1'),
    })
  })

  it('invalidates action comment queries after resolve', async () => {
    const queryClient = createTestQueryClient()
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

    const { result } = renderHook(() => useResolveActionCommentMutation('est-1', 'action-1'), {
      wrapper: ({ children }) =>
        createElement(QueryClientProvider, { client: queryClient }, children),
    })

    result.current.mutate('comment-2')

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: commentsQueryKeys.actionList('est-1', 'action-1'),
    })
  })

  it('invalidates action comment queries after unresolve', async () => {
    const queryClient = createTestQueryClient()
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

    const { result } = renderHook(() => useUnresolveActionCommentMutation('est-1', 'action-1'), {
      wrapper: ({ children }) =>
        createElement(QueryClientProvider, { client: queryClient }, children),
    })

    result.current.mutate('comment-2')

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: commentsQueryKeys.actionList('est-1', 'action-1'),
    })
  })
})
