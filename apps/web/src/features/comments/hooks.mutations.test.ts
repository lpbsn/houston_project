// @vitest-environment jsdom

import { renderHook, waitFor } from '@testing-library/react'
import { QueryClientProvider } from '@tanstack/react-query'
import { createElement } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { createTestQueryClient } from '@/test-utils'

import { commentsQueryKeys } from './api'
import { useCreateSignalCommentMutation } from './hooks'

const createSignalComment = vi.fn(async () => ({
  id: 'comment-1',
  origin: 'signal' as const,
  body: 'hello',
  author: { membership_id: 'm-1', display_name: 'Alice' },
  mentions: [],
  created_at: '2026-06-15T10:30:00Z',
}))

vi.mock('./api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('./api')>()
  return {
    ...actual,
    createSignalComment: (...args: unknown[]) => createSignalComment(...args),
  }
})

describe('useCreateSignalCommentMutation', () => {
  beforeEach(() => {
    createSignalComment.mockClear()
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

    expect(createSignalComment).toHaveBeenCalledWith('est-1', 'signal-1', {
      body: 'hello',
      mentioned_membership_ids: [],
    })
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: commentsQueryKeys.signalList('est-1', 'signal-1'),
    })
  })
})
