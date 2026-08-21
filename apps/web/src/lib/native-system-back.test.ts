// @vitest-environment jsdom

import { afterEach, describe, expect, it, vi } from 'vitest'

const isNativePlatform = vi.hoisted(() => vi.fn(() => false))
const getPlatform = vi.hoisted(() => vi.fn(() => 'web'))
const addListener = vi.hoisted(() =>
  vi.fn(async () => {
    return { remove: async () => undefined }
  }),
)
const minimizeApp = vi.hoisted(() => vi.fn(async () => undefined))

vi.mock('@capacitor/core', () => ({
  Capacitor: {
    isNativePlatform: () => isNativePlatform(),
    getPlatform: () => getPlatform(),
  },
}))

vi.mock('@capacitor/app', () => ({
  App: {
    addListener: (...args: unknown[]) => addListener(...(args as [string, () => void])),
    minimizeApp: () => minimizeApp(),
  },
}))

import { createMemoryHistory } from '@/app/app-history'
import { registerNativeOverlayDismiss, resetNativeOverlayDismissForTests } from './native-overlay-dismiss'
import {
  configureNativeSystemBack,
  resetNativeSystemBackForTests,
  setNativeSystemBackAuthGetter,
} from './native-system-back'

describe('native system back', () => {
  afterEach(async () => {
    await resetNativeSystemBackForTests()
    resetNativeOverlayDismissForTests()
    isNativePlatform.mockReset()
    isNativePlatform.mockReturnValue(false)
    getPlatform.mockReset()
    getPlatform.mockReturnValue('web')
    addListener.mockReset()
    addListener.mockImplementation(async () => ({ remove: async () => undefined }))
    minimizeApp.mockReset()
    vi.unstubAllEnvs()
  })

  async function configureAndroid(history = createMemoryHistory('/signals/sig-1')) {
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    isNativePlatform.mockReturnValue(true)
    getPlatform.mockReturnValue('android')
    let listener: (() => void) | undefined
    addListener.mockImplementation(async (_event, next) => {
      listener = next
      return { remove: async () => undefined }
    })
    await configureNativeSystemBack({ history })
    return { history, pressBack: () => listener?.() }
  }

  it('does not configure plugins for a native Vite build running off-device', async () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    isNativePlatform.mockReturnValue(false)

    await configureNativeSystemBack({ history: createMemoryHistory() })

    expect(addListener).not.toHaveBeenCalled()
  })

  it('does not configure plugins in web runtime even on a native platform', async () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'web')
    isNativePlatform.mockReturnValue(true)
    getPlatform.mockReturnValue('android')

    await configureNativeSystemBack({ history: createMemoryHistory() })

    expect(isNativePlatform).not.toHaveBeenCalled()
    expect(addListener).not.toHaveBeenCalled()
  })

  it('does not listen for backButton on iOS', async () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    isNativePlatform.mockReturnValue(true)
    getPlatform.mockReturnValue('ios')

    await configureNativeSystemBack({ history: createMemoryHistory('/signals/sig-1') })

    expect(addListener).not.toHaveBeenCalled()
  })

  it('dismisses an overlay without navigating', async () => {
    const { history, pressBack } = await configureAndroid()
    const dismiss = vi.fn()
    registerNativeOverlayDismiss(dismiss)

    pressBack()

    expect(dismiss).toHaveBeenCalledTimes(1)
    expect(history.getHref()).toBe('/signals/sig-1')
    expect(minimizeApp).not.toHaveBeenCalled()
  })

  it('navigates to the semantic back path instead of history.back', async () => {
    const { history, pressBack } = await configureAndroid(createMemoryHistory('/signals/sig-1'))

    pressBack()

    expect(history.getHref()).toBe('/signals')
    expect(minimizeApp).not.toHaveBeenCalled()
  })

  it('uses live auth extras when leaving analytics without operational access', async () => {
    const { history, pressBack } = await configureAndroid(createMemoryHistory('/analytics'))
    setNativeSystemBackAuthGetter(() => ({
      hasOperationalAccess: false,
      authenticatedLandingPath: '/organization',
    }))

    pressBack()

    expect(history.getHref()).toBe('/organization')
    expect(minimizeApp).not.toHaveBeenCalled()
  })

  it('resolves from live history after navigating to a hub instead of a stale back path', async () => {
    const { history, pressBack } = await configureAndroid(createMemoryHistory('/signals/sig-1'))

    pressBack()
    expect(history.getHref()).toBe('/signals')
    expect(minimizeApp).not.toHaveBeenCalled()

    pressBack()
    expect(history.getHref()).toBe('/signals')
    expect(minimizeApp).toHaveBeenCalledTimes(1)
  })

  it('minimizes when the semantic back path is already the current href', async () => {
    const { history, pressBack } = await configureAndroid(createMemoryHistory('/analytics'))
    setNativeSystemBackAuthGetter(() => ({
      hasOperationalAccess: false,
      authenticatedLandingPath: '/analytics',
    }))

    pressBack()

    expect(history.getHref()).toBe('/analytics')
    expect(minimizeApp).toHaveBeenCalledTimes(1)
  })

  it('minimizes on Dashboard hubs instead of forcing /general', async () => {
    const { history, pressBack } = await configureAndroid(createMemoryHistory('/cross'))
    setNativeSystemBackAuthGetter(() => ({ hasOperationalAccess: true }))

    pressBack()

    expect(history.getHref()).toBe('/cross')
    expect(minimizeApp).toHaveBeenCalledTimes(1)
  })

  it('minimizes on /analytics when operational access is present', async () => {
    const { history, pressBack } = await configureAndroid(createMemoryHistory('/analytics'))
    setNativeSystemBackAuthGetter(() => ({ hasOperationalAccess: true }))

    pressBack()

    expect(history.getHref()).toBe('/analytics')
    expect(minimizeApp).toHaveBeenCalledTimes(1)
  })

  it('minimizes on login', async () => {
    const { pressBack } = await configureAndroid(createMemoryHistory('/login'))

    pressBack()

    expect(minimizeApp).toHaveBeenCalledTimes(1)
  })

  it('leaves routing unchanged if addListener fails', async () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    isNativePlatform.mockReturnValue(true)
    getPlatform.mockReturnValue('android')
    addListener.mockRejectedValue(new Error('plugin'))

    await expect(
      configureNativeSystemBack({ history: createMemoryHistory('/signals/sig-1') }),
    ).rejects.toThrow('plugin')
  })
})
