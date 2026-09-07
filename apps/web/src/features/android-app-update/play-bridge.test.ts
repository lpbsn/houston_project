import { afterEach, describe, expect, it, vi } from 'vitest'

const { isNativePlatform, getPlatform, getAppRuntime } = vi.hoisted(() => ({
  isNativePlatform: vi.fn(() => true),
  getPlatform: vi.fn(() => 'android'),
  getAppRuntime: vi.fn(() => 'native' as const),
}))

vi.mock('@capacitor/core', () => ({
  Capacitor: {
    isNativePlatform: () => isNativePlatform(),
    getPlatform: () => getPlatform(),
  },
}))

vi.mock('@/lib/runtime', () => ({
  getAppRuntime: () => getAppRuntime(),
}))

import {
  isAndroidInAppUpdateRuntime,
  readAndroidPlayUpdate,
  setAndroidAppUpdatePluginLoaderForTests,
  startAndroidPlayUpdate,
} from './play-bridge'

describe('android play bridge', () => {
  afterEach(() => {
    setAndroidAppUpdatePluginLoaderForTests(null)
    isNativePlatform.mockReturnValue(true)
    getPlatform.mockReturnValue('android')
    getAppRuntime.mockReturnValue('native')
  })

  it('stays off on iOS and web', () => {
    getPlatform.mockReturnValue('ios')
    expect(isAndroidInAppUpdateRuntime()).toBe(false)
    getPlatform.mockReturnValue('web')
    getAppRuntime.mockReturnValue('web')
    isNativePlatform.mockReturnValue(false)
    expect(isAndroidInAppUpdateRuntime()).toBe(false)
  })

  it('maps Play info and starts a flexible update after a fresh check', async () => {
    const getAppUpdateInfo = vi.fn(async () => ({
      currentVersionCode: '2',
      availableVersionCode: '3',
      updateAvailability: 2,
      flexibleUpdateAllowed: true,
      immediateUpdateAllowed: false,
      installStatus: 0,
    }))
    const startFlexibleUpdate = vi.fn(async () => ({ code: 0 }))
    const performImmediateUpdate = vi.fn(async () => ({ code: 0 }))
    setAndroidAppUpdatePluginLoaderForTests(async () => ({
      getAppUpdateInfo,
      startFlexibleUpdate,
      performImmediateUpdate,
    }) as never)

    await expect(readAndroidPlayUpdate()).resolves.toMatchObject({
      currentVersionCode: '2',
      availableVersionCode: '3',
      flexibleUpdateAllowed: true,
    })
    await expect(startAndroidPlayUpdate('immediate')).resolves.toBe('ok')
    expect(getAppUpdateInfo).toHaveBeenCalledTimes(2)
    expect(startFlexibleUpdate).toHaveBeenCalledOnce()
    expect(performImmediateUpdate).not.toHaveBeenCalled()
  })

  it('maps cancel and failure without throwing', async () => {
    setAndroidAppUpdatePluginLoaderForTests(async () => ({
      getAppUpdateInfo: async () => ({
        currentVersionCode: '2',
        availableVersionCode: '3',
        updateAvailability: 2,
        flexibleUpdateAllowed: true,
        immediateUpdateAllowed: true,
      }),
      startFlexibleUpdate: async () => ({ code: 1 }),
      performImmediateUpdate: async () => ({ code: 2 }),
    }) as never)

    await expect(startAndroidPlayUpdate('flexible')).resolves.toBe('cancelled')
    await expect(startAndroidPlayUpdate('immediate')).resolves.toBe('failed')
  })

  it('returns null when Play lookup throws', async () => {
    setAndroidAppUpdatePluginLoaderForTests(async () => ({
      getAppUpdateInfo: async () => {
        throw new Error('not play')
      },
    }) as never)
    await expect(readAndroidPlayUpdate()).resolves.toBeNull()
  })
})
