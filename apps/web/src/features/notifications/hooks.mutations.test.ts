// @vitest-environment jsdom

import { renderHook, waitFor } from '@testing-library/react'
import { QueryClientProvider } from '@tanstack/react-query'
import { createElement } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { createTestQueryClient } from '@/test-utils'

import { notificationsQueryKeys } from './api'
import {
  useMarkAllNotificationsReadMutation,
  useMarkNotificationReadMutation,
  useUpdateNotificationPreferencesMutation,
} from './hooks'

const markNotificationRead = vi.fn(async () => ({
  id: 'notif-1',
  event_key: 'action_plan.execution.created',
  subject_type: 'action_plan_execution' as const,
  subject_id: 'exec-1',
  priority: 'info' as const,
  status: 'read' as const,
  title: 'Nouvelle exécution de plan',
  body: 'Une exécution de plan vous a été assignée.',
  actor: null,
  created_at: '2026-06-23T10:00:00.000Z',
  read_at: '2026-06-23T10:05:00.000Z',
  archived_at: null,
}))

const markAllNotificationsRead = vi.fn(async () => ({ updated_count: 2 }))
const updateNotificationPreferences = vi.fn(async () => ({ notifications_enabled: false }))

vi.mock('./api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('./api')>()
  return {
    ...actual,
    markNotificationRead: (...args: unknown[]) => markNotificationRead(...args),
    markAllNotificationsRead: (...args: unknown[]) => markAllNotificationsRead(...args),
    updateNotificationPreferences: (...args: unknown[]) =>
      updateNotificationPreferences(...args),
  }
})

describe('notification mutations', () => {
  beforeEach(() => {
    markNotificationRead.mockClear()
    markAllNotificationsRead.mockClear()
    updateNotificationPreferences.mockClear()
  })

  it('invalidates establishment notification lists after mark-read', async () => {
    const queryClient = createTestQueryClient()
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

    const { result } = renderHook(() => useMarkNotificationReadMutation('est-1'), {
      wrapper: ({ children }) =>
        createElement(QueryClientProvider, { client: queryClient }, children),
    })

    result.current.mutate('notif-1')

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    expect(markNotificationRead).toHaveBeenCalledWith('est-1', 'notif-1')
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: notificationsQueryKeys.lists('est-1'),
    })
  })

  it('invalidates establishment notification lists after mark-all-read', async () => {
    const queryClient = createTestQueryClient()
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

    const { result } = renderHook(() => useMarkAllNotificationsReadMutation('est-1'), {
      wrapper: ({ children }) =>
        createElement(QueryClientProvider, { client: queryClient }, children),
    })

    result.current.mutate()

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    expect(markAllNotificationsRead).toHaveBeenCalledWith('est-1')
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: notificationsQueryKeys.lists('est-1'),
    })
  })

  it('invalidates establishment notification preferences after update', async () => {
    const queryClient = createTestQueryClient()
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

    const { result } = renderHook(() => useUpdateNotificationPreferencesMutation('est-1'), {
      wrapper: ({ children }) =>
        createElement(QueryClientProvider, { client: queryClient }, children),
    })

    result.current.mutate({ notifications_enabled: false })

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    expect(updateNotificationPreferences).toHaveBeenCalledWith('est-1', {
      notifications_enabled: false,
    })
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: notificationsQueryKeys.preferences('est-1'),
    })
  })
})
