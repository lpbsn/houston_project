// @vitest-environment jsdom

import { afterEach, describe, expect, it, vi } from 'vitest'

const isNativePlatform = vi.hoisted(() => vi.fn(() => false))
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

vi.mock('@capacitor/keyboard', () => ({
  Keyboard: {
    addListener: (...args: unknown[]) =>
      addListener(...(args as [string, () => void])),
  },
}))

import {
  configureNativeKeyboard,
  getIsNativeKeyboardOpen,
  resetNativeKeyboardForTests,
  subscribeNativeKeyboard,
} from './native-keyboard'

describe('native keyboard', () => {
  afterEach(async () => {
    await resetNativeKeyboardForTests()
    isNativePlatform.mockReset()
    isNativePlatform.mockReturnValue(false)
    addListener.mockReset()
    addListener.mockImplementation(async () => ({ remove: async () => undefined }))
    vi.unstubAllEnvs()
  })

  it('stays closed without listeners when unconfigured', () => {
    expect(getIsNativeKeyboardOpen()).toBe(false)
    expect(addListener).not.toHaveBeenCalled()
  })

  it('does not configure plugins for a native Vite build running off-device', async () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    isNativePlatform.mockReturnValue(false)

    await configureNativeKeyboard()

    expect(getIsNativeKeyboardOpen()).toBe(false)
    expect(addListener).not.toHaveBeenCalled()
  })

  it('does not configure plugins in web runtime even on a native platform', async () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'web')
    isNativePlatform.mockReturnValue(true)

    await configureNativeKeyboard()

    expect(isNativePlatform).not.toHaveBeenCalled()
    expect(addListener).not.toHaveBeenCalled()
    expect(getIsNativeKeyboardOpen()).toBe(false)
  })

  it('opens on keyboardWillShow and closes on keyboardWillHide after native configuration', async () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    isNativePlatform.mockReturnValue(true)
    const listeners = new Map<string, () => void>()
    addListener.mockImplementation(async (event, next) => {
      listeners.set(event, next)
      return { remove: async () => undefined }
    })

    await configureNativeKeyboard()

    expect(getIsNativeKeyboardOpen()).toBe(false)
    expect(addListener).toHaveBeenCalledWith('keyboardWillShow', expect.any(Function))
    expect(addListener).toHaveBeenCalledWith('keyboardWillHide', expect.any(Function))

    const onChange = vi.fn()
    const stop = subscribeNativeKeyboard(onChange)

    listeners.get('keyboardWillShow')?.()
    expect(getIsNativeKeyboardOpen()).toBe(true)
    expect(onChange).toHaveBeenCalledTimes(1)

    listeners.get('keyboardWillHide')?.()
    expect(getIsNativeKeyboardOpen()).toBe(false)
    expect(onChange).toHaveBeenCalledTimes(2)

    stop()
  })

  it('leaves the keyboard closed if addListener fails', async () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    isNativePlatform.mockReturnValue(true)
    addListener.mockRejectedValue(new Error('plugin'))

    await expect(configureNativeKeyboard()).rejects.toThrow('plugin')

    expect(getIsNativeKeyboardOpen()).toBe(false)
  })

  it('removes the first listener if the second addListener fails', async () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    isNativePlatform.mockReturnValue(true)
    const remove = vi.fn(async () => undefined)
    addListener
      .mockResolvedValueOnce({ remove })
      .mockRejectedValueOnce(new Error('plugin'))

    await expect(configureNativeKeyboard()).rejects.toThrow('plugin')

    expect(remove).toHaveBeenCalledTimes(1)
    expect(getIsNativeKeyboardOpen()).toBe(false)
  })
})
