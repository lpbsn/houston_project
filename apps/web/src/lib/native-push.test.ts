// @vitest-environment jsdom

import { afterEach, describe, expect, it, vi } from 'vitest'

const isNativePlatform = vi.hoisted(() => vi.fn(() => false))
const getPlatform = vi.hoisted(() => vi.fn(() => 'ios'))
const getAccessToken = vi.hoisted(() => vi.fn(() => null as string | null))
const upsertPushDevice = vi.hoisted(() =>
  vi.fn(async () => ({
    id: 'device-1',
    platform: 'ios' as const,
    created_at: '2026-08-19T00:00:00Z',
    last_seen_at: '2026-08-19T00:00:00Z',
  })),
)
const revokePushDevice = vi.hoisted(() => vi.fn(async () => undefined))
const switchEstablishment = vi.hoisted(() => vi.fn(async () => undefined))
const markNotificationRead = vi.hoisted(() => vi.fn(async () => undefined))
const requestPermissions = vi.hoisted(() => vi.fn(async () => ({ receive: 'granted' as const })))
const checkPermissions = vi.hoisted(() => vi.fn(async () => ({ receive: 'granted' as const })))
const getToken = vi.hoisted(() => vi.fn(async () => ({ token: 'fcm-token-1' })))
const deleteToken = vi.hoisted(() => vi.fn(async () => undefined))
const addListener = vi.hoisted(() =>
  vi.fn(async (event: string, cb: (payload: unknown) => void) => {
    listeners[event] = cb
    return { remove: async () => undefined }
  }),
)
const listeners: Record<string, ((payload: unknown) => void) | undefined> = {}

vi.mock('@capacitor/core', () => ({
  Capacitor: {
    isNativePlatform: () => isNativePlatform(),
    getPlatform: () => getPlatform(),
  },
}))

vi.mock('@capacitor-firebase/messaging', () => ({
  FirebaseMessaging: {
    requestPermissions: (...args: unknown[]) => requestPermissions(...args),
    checkPermissions: (...args: unknown[]) => checkPermissions(...args),
    getToken: (...args: unknown[]) => getToken(...args),
    deleteToken: (...args: unknown[]) => deleteToken(...args),
    addListener: (...args: unknown[]) =>
      addListener(...(args as [string, (payload: unknown) => void])),
  },
}))

vi.mock('@/features/auth/session', () => ({
  getAccessToken: () => getAccessToken(),
}))

vi.mock('@/features/auth/api', () => ({
  switchEstablishment: (...args: unknown[]) => switchEstablishment(...args),
}))

vi.mock('@/features/notifications/api', () => ({
  markNotificationRead: (...args: unknown[]) => markNotificationRead(...args),
}))

vi.mock('@/features/notifications/push-devices-api', () => ({
  upsertPushDevice: (...args: unknown[]) => upsertPushDevice(...args),
  revokePushDevice: (...args: unknown[]) => revokePushDevice(...args),
}))

import { createMemoryHistory } from '@/app/app-history'
import {
  applyPendingNativePushTap,
  checkNativePushReceivePermission,
  optInNativePush,
  runNativePushBeforeLogout,
  setNativePushActiveEstablishmentGetter,
  setNativePushActiveUserIdGetter,
  syncNativePushTokenIfGranted,
} from './native-push-session'
import { configureNativePush, resetNativePushForTests } from './native-push'

describe('native push', () => {
  afterEach(async () => {
    await resetNativePushForTests()
    setNativePushActiveEstablishmentGetter(() => null)
    setNativePushActiveUserIdGetter(() => null)
    isNativePlatform.mockReset()
    isNativePlatform.mockReturnValue(false)
    getPlatform.mockReset()
    getPlatform.mockReturnValue('ios')
    getAccessToken.mockReset()
    getAccessToken.mockReturnValue(null)
    upsertPushDevice.mockClear()
    revokePushDevice.mockClear()
    switchEstablishment.mockClear()
    markNotificationRead.mockClear()
    requestPermissions.mockReset()
    requestPermissions.mockResolvedValue({ receive: 'granted' })
    checkPermissions.mockReset()
    checkPermissions.mockResolvedValue({ receive: 'granted' })
    getToken.mockReset()
    getToken.mockResolvedValue({ token: 'fcm-token-1' })
    deleteToken.mockReset()
    addListener.mockClear()
    for (const key of Object.keys(listeners)) {
      delete listeners[key]
    }
    vi.unstubAllEnvs()
  })

  it('does not configure plugins for a native Vite build running off-device', async () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    isNativePlatform.mockReturnValue(false)
    await configureNativePush({ history: createMemoryHistory() })
    expect(addListener).not.toHaveBeenCalled()
    expect(await checkNativePushReceivePermission()).toBe('unavailable')
  })

  it('buffers tokenReceived until a session exists then upserts', async () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    isNativePlatform.mockReturnValue(true)
    await configureNativePush({ history: createMemoryHistory() })

    listeners.tokenReceived?.({ token: 'fcm-token-1' })
    await Promise.resolve()
    expect(upsertPushDevice).not.toHaveBeenCalled()

    getAccessToken.mockReturnValue('access-token')
    await syncNativePushTokenIfGranted()

    expect(upsertPushDevice).toHaveBeenCalledOnce()
    expect(upsertPushDevice).toHaveBeenCalledWith({ token: 'fcm-token-1', platform: 'ios' })
  })

  it('does not POST again for an identical token', async () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    isNativePlatform.mockReturnValue(true)
    getAccessToken.mockReturnValue('access-token')
    setNativePushActiveUserIdGetter(() => 'user-1')
    await configureNativePush({ history: createMemoryHistory() })
    await syncNativePushTokenIfGranted()
    await syncNativePushTokenIfGranted()
    expect(upsertPushDevice).toHaveBeenCalledOnce()
  })

  it('re-upserts the same token after the session user changes', async () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    isNativePlatform.mockReturnValue(true)
    getAccessToken.mockReturnValue('access-token')
    setNativePushActiveUserIdGetter(() => 'user-a')
    await configureNativePush({ history: createMemoryHistory() })
    await syncNativePushTokenIfGranted()
    expect(upsertPushDevice).toHaveBeenCalledOnce()

    setNativePushActiveUserIdGetter(() => 'user-b')
    await syncNativePushTokenIfGranted()

    expect(upsertPushDevice).toHaveBeenCalledTimes(2)
    expect(upsertPushDevice).toHaveBeenNthCalledWith(2, { token: 'fcm-token-1', platform: 'ios' })
    expect(revokePushDevice).not.toHaveBeenCalled()
  })

  it('re-upserts on opt-in after the session user changes', async () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    isNativePlatform.mockReturnValue(true)
    getAccessToken.mockReturnValue('access-token')
    setNativePushActiveUserIdGetter(() => 'user-a')
    await configureNativePush({ history: createMemoryHistory() })
    await syncNativePushTokenIfGranted()

    setNativePushActiveUserIdGetter(() => 'user-b')
    await optInNativePush()

    expect(upsertPushDevice).toHaveBeenCalledTimes(2)
    expect(revokePushDevice).not.toHaveBeenCalled()
  })

  it('rotates by upserting the new token and revoking the previous device', async () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    isNativePlatform.mockReturnValue(true)
    getAccessToken.mockReturnValue('access-token')
    await configureNativePush({ history: createMemoryHistory() })
    await syncNativePushTokenIfGranted()

    upsertPushDevice.mockResolvedValueOnce({
      id: 'device-2',
      platform: 'ios',
      created_at: '2026-08-19T00:00:00Z',
      last_seen_at: '2026-08-19T00:00:00Z',
    })
    listeners.tokenReceived?.({ token: 'fcm-token-2' })
    await vi.waitFor(() => {
      expect(upsertPushDevice).toHaveBeenCalledWith({ token: 'fcm-token-2', platform: 'ios' })
    })
    expect(revokePushDevice).toHaveBeenCalledWith('device-1')
  })

  it('syncs when OS permission is granted even if the active establishment is opt-out', async () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    isNativePlatform.mockReturnValue(true)
    getAccessToken.mockReturnValue('access-token')
    await configureNativePush({ history: createMemoryHistory() })
    await syncNativePushTokenIfGranted()
    expect(upsertPushDevice).toHaveBeenCalledOnce()
  })

  it('does not upsert when OS permission is not granted', async () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    isNativePlatform.mockReturnValue(true)
    getAccessToken.mockReturnValue('access-token')
    checkPermissions.mockResolvedValue({ receive: 'denied' })
    await configureNativePush({ history: createMemoryHistory() })
    await syncNativePushTokenIfGranted()
    expect(upsertPushDevice).not.toHaveBeenCalled()
  })

  it('revokes then deletes the local token on logout', async () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    isNativePlatform.mockReturnValue(true)
    getAccessToken.mockReturnValue('access-token')
    await configureNativePush({ history: createMemoryHistory() })
    await syncNativePushTokenIfGranted()
    await runNativePushBeforeLogout()
    expect(revokePushDevice).toHaveBeenCalledWith('device-1')
    expect(deleteToken).toHaveBeenCalledOnce()
  })

  it('does not upsert when opt-in permission is denied', async () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    isNativePlatform.mockReturnValue(true)
    getAccessToken.mockReturnValue('access-token')
    requestPermissions.mockResolvedValue({ receive: 'denied' })
    await configureNativePush({ history: createMemoryHistory() })
    await expect(optInNativePush()).rejects.toThrow('Notification permission was not granted.')
    expect(upsertPushDevice).not.toHaveBeenCalled()
  })

  it('holds a cold-start tap until session is ready then navigates the payload url', async () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    isNativePlatform.mockReturnValue(true)
    const history = createMemoryHistory('/profile')
    await configureNativePush({ history })
    setNativePushActiveEstablishmentGetter(() => 'est-1')

    listeners.notificationActionPerformed?.({
      notification: {
        data: {
          notification_id: 'n1',
          event_key: 'signal.created',
          establishment_id: 'est-2',
          url: '/signals/s1',
        },
      },
    })
    await Promise.resolve()
    expect(switchEstablishment).not.toHaveBeenCalled()
    expect(history.getHref()).toBe('/profile')

    getAccessToken.mockReturnValue('access-token')
    await applyPendingNativePushTap()

    expect(switchEstablishment).toHaveBeenCalledWith({ establishment_id: 'est-2' })
    expect(history.getHref()).toBe('/signals/s1')
    expect(markNotificationRead).toHaveBeenCalledWith('est-2', 'n1')
  })
})
