// @vitest-environment jsdom

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClientProvider } from '@tanstack/react-query'
import { createElement } from 'react'

import { createTestQueryClient } from '@/test-utils'

import { useCreateChecklistTemplateMutation } from './hooks'

const createChecklistTemplate = vi.fn(async () => ({ id: 'template-1' }))

vi.mock('./api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('./api')>()
  return {
    ...actual,
    createChecklistTemplate: (...args: unknown[]) => createChecklistTemplate(...args),
  }
})

describe('useCreateChecklistTemplateMutation', () => {
  beforeEach(() => {
    createChecklistTemplate.mockClear()
  })

  it('invalidates establishment-scoped checklist and action queries on success', async () => {
    const queryClient = createTestQueryClient()
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

    const { result } = renderHook(() => useCreateChecklistTemplateMutation('est-1'), {
      wrapper: ({ children }) =>
        createElement(QueryClientProvider, { client: queryClient }, children),
    })

    result.current.mutate({
      title: 'Opening',
      description: 'Daily opening checklist',
    })

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    expect(createChecklistTemplate).toHaveBeenCalled()
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['checklists', 'templates', 'est-1'] })
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ['actions', 'execution-feed', 'est-1'],
    })
    expect(invalidateSpy).not.toHaveBeenCalledWith({ queryKey: ['checklists'] })
    expect(invalidateSpy).not.toHaveBeenCalledWith({ queryKey: ['actions'] })
  })
})
