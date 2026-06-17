// @vitest-environment jsdom

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClientProvider } from '@tanstack/react-query'
import { createElement } from 'react'

import { createTestQueryClient } from '@/test-utils'

import {
  useCreateChecklistTemplateMutation,
  useScheduleChecklistFromTemplateMutation,
} from './hooks'

const createChecklistTemplate = vi.fn(async () => ({ id: 'template-1' }))
const scheduleChecklistFromTemplate = vi.fn()

vi.mock('./api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('./api')>()
  return {
    ...actual,
    createChecklistTemplate: (...args: unknown[]) => createChecklistTemplate(...args),
    scheduleChecklistFromTemplate: (...args: unknown[]) => scheduleChecklistFromTemplate(...args),
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

describe('useScheduleChecklistFromTemplateMutation', () => {
  beforeEach(() => {
    scheduleChecklistFromTemplate.mockReset()
  })

  it('invalidates checklist assignment surfaces on recurring success', async () => {
    scheduleChecklistFromTemplate.mockResolvedValue({
      result_type: 'assignment',
      assignment: { id: 'assign-1' },
      execution: null,
    })

    const queryClient = createTestQueryClient()
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

    const { result } = renderHook(
      () => useScheduleChecklistFromTemplateMutation('est-1', 'tpl-1'),
      {
        wrapper: ({ children }) =>
          createElement(QueryClientProvider, { client: queryClient }, children),
      },
    )

    result.current.mutate({
      assigned_to: 'member-1',
      start_at: '09:00:00',
      end_at: '10:00:00',
      recurrence_days: ['monday'],
      recurrence_end_date: '2026-06-30',
    })

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ['checklists', 'assignments', 'est-1'],
    })
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ['checklists', 'template-detail', 'est-1', 'tpl-1'],
    })
  })

  it('invalidates execution detail surfaces on one-shot success', async () => {
    scheduleChecklistFromTemplate.mockResolvedValue({
      result_type: 'execution',
      execution: { id: 'exec-1' },
      assignment: null,
    })

    const queryClient = createTestQueryClient()
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

    const { result } = renderHook(
      () => useScheduleChecklistFromTemplateMutation('est-1', 'tpl-1'),
      {
        wrapper: ({ children }) =>
          createElement(QueryClientProvider, { client: queryClient }, children),
      },
    )

    result.current.mutate({
      assigned_to: 'member-1',
      start_at: '09:00:00',
      end_at: '10:00:00',
    })

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ['checklists', 'execution-detail', 'est-1', 'exec-1'],
    })
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ['actions', 'execution-feed', 'est-1'],
    })
  })
})
