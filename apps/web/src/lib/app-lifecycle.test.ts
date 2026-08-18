// @vitest-environment jsdom

import { afterEach, describe, expect, it, vi } from 'vitest'

const isNativePlatform = vi.hoisted(() => vi.fn(() => false))
const getState = vi.hoisted(() => vi.fn(async () => ({ isActive: true })))
const addListener = vi.hoisted(() =>
  vi.fn(async () => {
    return { remove: async () => undefined }
  }),
)

vi.mock('@capacitor/core', () => ({
  Capacitor: {
    isNativePlatform: () => isNativePlatform(),
  },
}))

vi.mock('@capacitor/app', () => ({
  App: {
    getState: (...args: unknown[]) => getState(...args),
    addListener: (...args: unknown[]) => addListener(...(args as [string, (state: { isActive: boolean }) => void])),
  },
}))

import {
  configureNativeAppLifecycle,
  getIsAppActive,
  resetAppLifecycleForTests,
  subscribeAppBackground,
  subscribeAppForeground,
  usesNativeAppLifecycle,
} from './app-lifecycle'

describe('app lifecycle', () => {
  afterEach(async () => {
    await resetAppLifecycleForTests()
    isNativePlatform.mockReset()
    isNativePlatform.mockReturnValue(false)
    getState.mockReset()
    getState.mockResolvedValue({ isActive: true })
    addListener.mockReset()
    addListener.mockImplementation(async () => ({ remove: async () => undefined }))
    vi.unstubAllEnvs()
  })

  it('notifies web subscribers on visibilitychange', () => {
    const onForeground = vi.fn()
    const onBackground = vi.fn()
    const stopForeground = subscribeAppForeground(onForeground)
    const stopBackground = subscribeAppBackground(onBackground)

    Object.defineProperty(document, 'visibilityState', {
      configurable: true,
      value: 'hidden',
    })
    document.dispatchEvent(new Event('visibilitychange'))
    expect(onBackground).toHaveBeenCalledTimes(1)
    expect(onForeground).not.toHaveBeenCalled()

    Object.defineProperty(document, 'visibilityState', {
      configurable: true,
      value: 'visible',
    })
    document.dispatchEvent(new Event('visibilitychange'))
    expect(onForeground).toHaveBeenCalledTimes(1)

    stopForeground()
    stopBackground()
  })

  it('does not configure plugins for a native Vite build running off-device', async () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    isNativePlatform.mockReturnValue(false)

    await configureNativeAppLifecycle()

    expect(usesNativeAppLifecycle()).toBe(false)
    expect(addListener).not.toHaveBeenCalled()
  })

  it('does not configure plugins in web runtime even on a native platform', async () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'web')
    isNativePlatform.mockReturnValue(true)

    await configureNativeAppLifecycle()

    expect(isNativePlatform).not.toHaveBeenCalled()
    expect(addListener).not.toHaveBeenCalled()
  })

  it('uses appStateChange after native configuration', async () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    isNativePlatform.mockReturnValue(true)
    let listener: ((state: { isActive: boolean }) => void) | undefined
    addListener.mockImplementation(async (_event, next) => {
      listener = next
      return { remove: async () => undefined }
    })

    await configureNativeAppLifecycle()

    expect(usesNativeAppLifecycle()).toBe(true)
    expect(getIsAppActive()).toBe(true)
    expect(addListener).toHaveBeenCalledWith('appStateChange', expect.any(Function))

    const onForeground = vi.fn()
    const onBackground = vi.fn()
    subscribeAppForeground(onForeground)
    subscribeAppBackground(onBackground)

    listener?.({ isActive: false })
    expect(getIsAppActive()).toBe(false)
    expect(onBackground).toHaveBeenCalledTimes(1)

    listener?.({ isActive: true })
    expect(getIsAppActive()).toBe(true)
    expect(onForeground).toHaveBeenCalledTimes(1)

    Object.defineProperty(document, 'visibilityState', {
      configurable: true,
      value: 'hidden',
    })
    document.dispatchEvent(new Event('visibilitychange'))
    expect(onBackground).toHaveBeenCalledTimes(1)
  })
})
