// @vitest-environment jsdom

import { renderHook, waitFor } from '@testing-library/react'
import { QueryClientProvider } from '@tanstack/react-query'
import { createElement } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { createTestQueryClient } from '@/test-utils'

import { pushQueryKeys, useWebPushToggle } from './hooks'

const registerWebPushSubscription = vi.fn(async () => ({} as PushSubscription))
const getLocalPushSubscription = vi.fn(async () => null)
const mutatePreferences = vi.fn()
const mutatePreferencesAsync = vi.fn(async (input: { push_enabled?: boolean }) => ({
  notifications_enabled: true,
  push_enabled: input.push_enabled ?? false,
}))

vi.mock('./lib/subscription', () => ({
  registerWebPushSubscription: () => registerWebPushSubscription(),
}))

vi.mock('./lib/local-subscription', () => ({
  getLocalPushSubscription: () => getLocalPushSubscription(),
}))

vi.mock('@/features/notifications/hooks', () => ({
  useUpdateNotificationPreferencesMutation: () => ({
    mutate: mutatePreferences,
    mutateAsync: mutatePreferencesAsync,
    isPending: false,
    isError: false,
  }),
}))

vi.mock('./lib/support', async (importOriginal) => {
  const actual = await importOriginal<typeof import('./lib/support')>()
  return {
    ...actual,
    getBrowserPushSupportEnvironment: () => ({
      isIosDevice: false,
      isStandalonePwa: false,
      hasServiceWorker: true,
      hasPushManager: true,
      hasNotification: true,
      permission: 'granted' as NotificationPermission,
    }),
  }
})

describe('useWebPushToggle', () => {
  beforeEach(() => {
    registerWebPushSubscription.mockClear()
    getLocalPushSubscription.mockClear()
    mutatePreferences.mockClear()
    mutatePreferencesAsync.mockClear()
    getLocalPushSubscription.mockResolvedValue(null)
  })

  it('enables push through subscribe, upsert, and preferences patch', async () => {
    const queryClient = createTestQueryClient()
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

    const { result } = renderHook(
      () =>
        useWebPushToggle('est-1', { notifications_enabled: true, push_enabled: false }),
      {
        wrapper: ({ children }) =>
          createElement(QueryClientProvider, { client: queryClient }, children),
      },
    )

    result.current.onToggle(true)

    await waitFor(() => {
      expect(registerWebPushSubscription).toHaveBeenCalledTimes(1)
    })

    expect(mutatePreferencesAsync).toHaveBeenCalledWith({ push_enabled: true })
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: pushQueryKeys.localSubscription,
    })
  })

  it('disables push with preferences patch only', async () => {
    const queryClient = createTestQueryClient()

    const { result } = renderHook(
      () =>
        useWebPushToggle('est-1', { notifications_enabled: true, push_enabled: true }),
      {
        wrapper: ({ children }) =>
          createElement(QueryClientProvider, { client: queryClient }, children),
      },
    )

    await waitFor(() => {
      expect(result.current.state).toBe('disabled')
    })

    result.current.onToggle(false)

    expect(mutatePreferences).toHaveBeenCalledWith({ push_enabled: false })
    expect(registerWebPushSubscription).not.toHaveBeenCalled()
  })
})
