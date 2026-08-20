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
  setNativeSystemBackHrefGetter,
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

  it('uses the live getter when App has registered a back href', async () => {
    const { history, pressBack } = await configureAndroid(createMemoryHistory('/signals/sig-1'))
    setNativeSystemBackHrefGetter(() => '/analytics')

    pressBack()

    expect(history.getHref()).toBe('/analytics')
  })

  it('minimizes on a terrain hub with no back path', async () => {
    const { history, pressBack } = await configureAndroid(createMemoryHistory('/reporting'))

    pressBack()

    expect(history.getHref()).toBe('/reporting')
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
