// @vitest-environment jsdom

import { renderHook, waitFor } from '@testing-library/react'
import { QueryClientProvider } from '@tanstack/react-query'
import { createElement } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { createTestQueryClient } from '@/test-utils'

import { pushQueryKeys, useWebPushToggle } from './hooks'
import type { PushSupportEnvironment } from './lib/support'

const pushSubscription = {
  unsubscribe: vi.fn(async () => true),
} as unknown as PushSubscription
const webPushRegistration = {
  pushSubscription,
  serverSubscription: {
    id: 'sub-1',
    endpoint: 'https://push.example/sub-1',
    created_at: '2026-01-01T00:00:00Z',
    last_seen_at: null,
  },
}
const registerWebPushSubscription = vi.fn(async () => webPushRegistration)
const rollbackWebPushRegistration = vi.fn(async () => undefined)
const getLocalPushSubscription = vi.fn(async () => null)
const mutatePreferences = vi.fn()
const mutatePreferencesAsync = vi.fn(async (input: { push_enabled?: boolean }) => ({
  notifications_enabled: true,
  push_enabled: input.push_enabled ?? false,
}))
const resetPreferencesMutation = vi.fn()
const getBrowserPushSupportEnvironment = vi.fn<() => PushSupportEnvironment>(() => ({
  isIosDevice: false,
  isStandalonePwa: false,
  hasServiceWorker: true,
  hasPushManager: true,
  hasNotification: true,
  permission: 'granted',
}))

vi.mock('./lib/subscription', () => ({
  registerWebPushSubscription: () => registerWebPushSubscription(),
  rollbackWebPushRegistration: (registration: typeof webPushRegistration) =>
    rollbackWebPushRegistration(registration),
}))

vi.mock('./lib/local-subscription', () => ({
  getLocalPushSubscription: () => getLocalPushSubscription(),
}))

vi.mock('@/features/notifications/hooks', () => ({
  useUpdateNotificationPreferencesMutation: () => ({
    mutate: mutatePreferences,
    mutateAsync: mutatePreferencesAsync,
    reset: resetPreferencesMutation,
    isPending: false,
    isError: false,
  }),
}))

vi.mock('./lib/support', async (importOriginal) => {
  const actual = await importOriginal<typeof import('./lib/support')>()
  return {
    ...actual,
    getBrowserPushSupportEnvironment: () => getBrowserPushSupportEnvironment(),
  }
})

describe('useWebPushToggle', () => {
  beforeEach(() => {
    registerWebPushSubscription.mockClear()
    rollbackWebPushRegistration.mockClear()
    getLocalPushSubscription.mockClear()
    mutatePreferences.mockClear()
    mutatePreferencesAsync.mockClear()
    resetPreferencesMutation.mockClear()
    getBrowserPushSupportEnvironment.mockClear()
    getBrowserPushSupportEnvironment.mockReturnValue({
      isIosDevice: false,
      isStandalonePwa: false,
      hasServiceWorker: true,
      hasPushManager: true,
      hasNotification: true,
      permission: 'granted',
    })
    getLocalPushSubscription.mockResolvedValue(null)
    mutatePreferencesAsync.mockResolvedValue({
      notifications_enabled: true,
      push_enabled: true,
    })
    registerWebPushSubscription.mockResolvedValue(webPushRegistration)
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

  it('refreshes browser permission after first-time enable', async () => {
    const queryClient = createTestQueryClient()
    let permission: NotificationPermission = 'default'
    getBrowserPushSupportEnvironment.mockImplementation(() => ({
      isIosDevice: false,
      isStandalonePwa: false,
      hasServiceWorker: true,
      hasPushManager: true,
      hasNotification: true,
      permission,
    }))
    registerWebPushSubscription.mockImplementation(async () => {
      permission = 'granted'
      return webPushRegistration
    })
    getLocalPushSubscription.mockResolvedValue(pushSubscription)

    const { result, rerender } = renderHook(
      ({ pushEnabled }) =>
        useWebPushToggle('est-1', {
          notifications_enabled: true,
          push_enabled: pushEnabled,
        }),
      {
        initialProps: { pushEnabled: false },
        wrapper: ({ children }) =>
          createElement(QueryClientProvider, { client: queryClient }, children),
      },
    )

    await waitFor(() => {
      expect(result.current.state).toBe('disabled')
    })

    result.current.onToggle(true)

    await waitFor(() => {
      expect(registerWebPushSubscription).toHaveBeenCalledTimes(1)
    })

    rerender({ pushEnabled: true })

    await waitFor(() => {
      expect(result.current.checked).toBe(true)
    })
  })

  it('clears enable error after successful disable', async () => {
    const queryClient = createTestQueryClient()
    registerWebPushSubscription.mockRejectedValueOnce(new Error('enable failed'))

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
      expect(result.current.isError).toBe(true)
      expect(result.current.errorMessage).toBe('enable failed')
    })

    result.current.onToggle(false)

    await waitFor(() => {
      expect(result.current.isError).toBe(false)
      expect(result.current.errorMessage).toBeNull()
    })
  })

  it('rolls back the push registration when preferences patch fails', async () => {
    const queryClient = createTestQueryClient()
    const patchError = new Error('patch failed')
    mutatePreferencesAsync.mockRejectedValueOnce(patchError)

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
      expect(rollbackWebPushRegistration).toHaveBeenCalledWith(webPushRegistration)
    })

    await waitFor(() => {
      expect(result.current.isError).toBe(true)
      expect(result.current.errorMessage).toBe('patch failed')
    })
  })

  it('preserves original patch error when rollback cleanup also fails', async () => {
    const queryClient = createTestQueryClient()
    const patchError = new Error('patch failed')
    mutatePreferencesAsync.mockRejectedValueOnce(patchError)

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
      expect(rollbackWebPushRegistration).toHaveBeenCalledWith(webPushRegistration)
    })

    await waitFor(() => {
      expect(result.current.isError).toBe(true)
      expect(result.current.errorMessage).toBe('patch failed')
    })
  })
})
