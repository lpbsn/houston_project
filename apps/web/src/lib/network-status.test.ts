// @vitest-environment jsdom

import { act, renderHook } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { onlineManager } from '@tanstack/react-query'

const isNativePlatform = vi.hoisted(() => vi.fn(() => false))
const getStatus = vi.hoisted(() => vi.fn(async () => ({ connected: true, connectionType: 'wifi' as const })))
const addListener = vi.hoisted(() =>
  vi.fn(async () => {
    return { remove: async () => undefined }
  }),
)
const isAppActive = vi.hoisted(() => ({ current: true }))
const appForegroundListeners = vi.hoisted(() => ({ current: [] as Array<() => void> }))
const appBackgroundListeners = vi.hoisted(() => ({ current: [] as Array<() => void> }))

vi.mock('@capacitor/core', () => ({
  Capacitor: {
    isNativePlatform: () => isNativePlatform(),
  },
}))

vi.mock('@capacitor/network', () => ({
  Network: {
    getStatus: (...args: unknown[]) => getStatus(...args),
    addListener: (...args: unknown[]) =>
      addListener(...(args as [string, (status: { connected: boolean }) => void])),
  },
}))

vi.mock('@/lib/app-lifecycle', () => ({
  getIsAppActive: () => isAppActive.current,
  subscribeAppForeground: (listener: () => void) => {
    appForegroundListeners.current.push(listener)
    return () => {
      appForegroundListeners.current = appForegroundListeners.current.filter((item) => item !== listener)
    }
  },
  subscribeAppBackground: (listener: () => void) => {
    appBackgroundListeners.current.push(listener)
    return () => {
      appBackgroundListeners.current = appBackgroundListeners.current.filter((item) => item !== listener)
    }
  },
}))

import {
  configureNativeNetworkStatus,
  getIsOnline,
  resetNetworkStatusForTests,
  subscribeNetworkOnline,
  useNetworkStatus,
} from './network-status'

describe('useNetworkStatus', () => {
  afterEach(async () => {
    await resetNetworkStatusForTests()
    isNativePlatform.mockReset()
    isNativePlatform.mockReturnValue(false)
    getStatus.mockReset()
    getStatus.mockResolvedValue({ connected: true, connectionType: 'wifi' })
    addListener.mockReset()
    addListener.mockImplementation(async () => ({ remove: async () => undefined }))
    isAppActive.current = true
    appForegroundListeners.current = []
    appBackgroundListeners.current = []
    vi.useRealTimers()
    vi.restoreAllMocks()
    vi.unstubAllEnvs()
  })

  it('reflects navigator.onLine and updates on offline/online events', () => {
    Object.defineProperty(navigator, 'onLine', {
      configurable: true,
      value: true,
    })

    const { result } = renderHook(() => useNetworkStatus())
    expect(result.current.isOnline).toBe(true)

    act(() => {
      Object.defineProperty(navigator, 'onLine', {
        configurable: true,
        value: false,
      })
      window.dispatchEvent(new Event('offline'))
    })

    expect(result.current.isOnline).toBe(false)

    act(() => {
      Object.defineProperty(navigator, 'onLine', {
        configurable: true,
        value: true,
      })
      window.dispatchEvent(new Event('online'))
    })

    expect(result.current.isOnline).toBe(true)
  })

  it('does not configure plugins for a native Vite build running off-device', async () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    isNativePlatform.mockReturnValue(false)

    await configureNativeNetworkStatus()

    expect(addListener).not.toHaveBeenCalled()
  })

  it('uses Network plugin status for banner and Query onlineManager', async () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    isNativePlatform.mockReturnValue(true)
    getStatus.mockResolvedValue({ connected: true, connectionType: 'wifi' })
    let listener: ((status: { connected: boolean }) => void) | undefined
    addListener.mockImplementation(async (_event, next) => {
      listener = next
      return { remove: async () => undefined }
    })

    await configureNativeNetworkStatus()

    const { result } = renderHook(() => useNetworkStatus())
    expect(result.current.isOnline).toBe(true)
    expect(onlineManager.isOnline()).toBe(true)

    act(() => {
      listener?.({ connected: false })
    })

    expect(result.current.isOnline).toBe(false)
    expect(onlineManager.isOnline()).toBe(false)

    Object.defineProperty(navigator, 'onLine', {
      configurable: true,
      value: true,
    })
    act(() => {
      window.dispatchEvent(new Event('online'))
    })

    expect(result.current.isOnline).toBe(false)
    expect(onlineManager.isOnline()).toBe(false)

    act(() => {
      listener?.({ connected: true })
    })

    expect(result.current.isOnline).toBe(true)
    expect(onlineManager.isOnline()).toBe(true)
  })

  it('exposes getIsOnline from the native Network snapshot', async () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    isNativePlatform.mockReturnValue(true)
    getStatus.mockResolvedValue({ connected: true, connectionType: 'wifi' })
    let listener: ((status: { connected: boolean }) => void) | undefined
    addListener.mockImplementation(async (_event, next) => {
      listener = next
      return { remove: async () => undefined }
    })

    await configureNativeNetworkStatus()

    expect(getIsOnline()).toBe(true)

    act(() => {
      listener?.({ connected: false })
    })
    expect(getIsOnline()).toBe(false)

    act(() => {
      listener?.({ connected: true })
    })
    expect(getIsOnline()).toBe(true)
  })

  it('notifies subscribeNetworkOnline on native offline-to-online, not window online', async () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    isNativePlatform.mockReturnValue(true)
    getStatus.mockResolvedValue({ connected: false, connectionType: 'wifi' })
    let listener: ((status: { connected: boolean }) => void) | undefined
    addListener.mockImplementation(async (_event, next) => {
      listener = next
      return { remove: async () => undefined }
    })

    await configureNativeNetworkStatus()

    const onOnline = vi.fn()
    const unsubscribe = subscribeNetworkOnline(onOnline)

    act(() => {
      window.dispatchEvent(new Event('online'))
    })
    expect(onOnline).not.toHaveBeenCalled()

    act(() => {
      listener?.({ connected: true })
    })
    expect(onOnline).toHaveBeenCalledTimes(1)

    act(() => {
      listener?.({ connected: true })
    })
    expect(onOnline).toHaveBeenCalledTimes(1)

    unsubscribe()
  })

  it('leaves window online as the source if addListener fails', async () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    isNativePlatform.mockReturnValue(true)
    addListener.mockRejectedValue(new Error('plugin'))
    Object.defineProperty(navigator, 'onLine', {
      configurable: true,
      value: true,
    })

    await expect(configureNativeNetworkStatus()).rejects.toThrow('plugin')

    const onOnline = vi.fn()
    const unsubscribe = subscribeNetworkOnline(onOnline)
    act(() => {
      window.dispatchEvent(new Event('online'))
    })
    expect(onOnline).toHaveBeenCalledTimes(1)
    unsubscribe()
  })

  it('removes the plugin listener and stays on window online if getStatus fails', async () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    isNativePlatform.mockReturnValue(true)
    const remove = vi.fn(async () => undefined)
    addListener.mockImplementation(async () => ({ remove }))
    getStatus.mockRejectedValue(new Error('status'))

    await expect(configureNativeNetworkStatus()).rejects.toThrow('status')

    expect(remove).toHaveBeenCalledTimes(1)
    const onOnline = vi.fn()
    const unsubscribe = subscribeNetworkOnline(onOnline)
    act(() => {
      window.dispatchEvent(new Event('online'))
    })
    expect(onOnline).toHaveBeenCalledTimes(1)
    unsubscribe()
  })

  it('prefers networkStatusChange received during configuration over a stale snapshot', async () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    isNativePlatform.mockReturnValue(true)
    let listener: ((status: { connected: boolean }) => void) | undefined
    let resolveStatus: (value: { connected: boolean; connectionType: 'wifi' }) => void = () => {}
    addListener.mockImplementation(async (_event, next) => {
      listener = next
      return { remove: async () => undefined }
    })
    getStatus.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveStatus = resolve
        }),
    )

    const configuring = configureNativeNetworkStatus()
    await vi.waitFor(() => {
      expect(listener).toBeDefined()
    })
    listener?.({ connected: false })
    resolveStatus({ connected: true, connectionType: 'wifi' })
    await configuring

    const { result } = renderHook(() => useNetworkStatus())
    expect(result.current.isOnline).toBe(false)
    expect(onlineManager.isOnline()).toBe(false)
  })

  it('recovers banner, Query, and subscribeNetworkOnline from a foreground getStatus without a listener event', async () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    isNativePlatform.mockReturnValue(true)
    getStatus.mockResolvedValue({ connected: true, connectionType: 'wifi' })
    let listener: ((status: { connected: boolean }) => void) | undefined
    addListener.mockImplementation(async (_event, next) => {
      listener = next
      return { remove: async () => undefined }
    })

    await configureNativeNetworkStatus()
    const { result } = renderHook(() => useNetworkStatus())
    const onOnline = vi.fn()
    const unsubscribe = subscribeNetworkOnline(onOnline)

    act(() => {
      listener?.({ connected: false })
    })
    expect(result.current.isOnline).toBe(false)
    expect(onlineManager.isOnline()).toBe(false)

    getStatus.mockClear()
    getStatus.mockResolvedValue({ connected: true, connectionType: 'wifi' })
    await act(async () => {
      for (const onForeground of appForegroundListeners.current) {
        onForeground()
      }
      await Promise.resolve()
    })

    expect(getStatus).toHaveBeenCalledTimes(1)
    expect(result.current.isOnline).toBe(true)
    expect(onlineManager.isOnline()).toBe(true)
    expect(onOnline).toHaveBeenCalledTimes(1)
    unsubscribe()
  })

  it('retries once after a successful offline foreground getStatus', async () => {
    vi.useFakeTimers()
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    isNativePlatform.mockReturnValue(true)
    getStatus.mockResolvedValue({ connected: true, connectionType: 'wifi' })
    let listener: ((status: { connected: boolean }) => void) | undefined
    addListener.mockImplementation(async (_event, next) => {
      listener = next
      return { remove: async () => undefined }
    })

    await configureNativeNetworkStatus()
    const { result } = renderHook(() => useNetworkStatus())
    const onOnline = vi.fn()
    const unsubscribe = subscribeNetworkOnline(onOnline)

    act(() => {
      listener?.({ connected: false })
    })

    getStatus.mockReset()
    getStatus.mockResolvedValueOnce({ connected: false, connectionType: 'wifi' })
    await act(async () => {
      for (const onForeground of appForegroundListeners.current) {
        onForeground()
      }
      await Promise.resolve()
    })
    expect(result.current.isOnline).toBe(false)
    expect(onlineManager.isOnline()).toBe(false)
    expect(onOnline).not.toHaveBeenCalled()

    getStatus.mockResolvedValueOnce({ connected: true, connectionType: 'wifi' })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000)
    })

    expect(result.current.isOnline).toBe(true)
    expect(onlineManager.isOnline()).toBe(true)
    expect(onOnline).toHaveBeenCalledTimes(1)

    getStatus.mockResolvedValue({ connected: true, connectionType: 'wifi' })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000)
    })
    expect(onOnline).toHaveBeenCalledTimes(1)
    expect(getStatus).toHaveBeenCalledTimes(2)
    unsubscribe()
  })

  it('ignores a late foreground getStatus after a newer networkStatusChange', async () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    isNativePlatform.mockReturnValue(true)
    getStatus.mockResolvedValue({ connected: true, connectionType: 'wifi' })
    let listener: ((status: { connected: boolean }) => void) | undefined
    addListener.mockImplementation(async (_event, next) => {
      listener = next
      return { remove: async () => undefined }
    })

    await configureNativeNetworkStatus()
    const { result } = renderHook(() => useNetworkStatus())
    const onOnline = vi.fn()
    const unsubscribe = subscribeNetworkOnline(onOnline)

    act(() => {
      listener?.({ connected: false })
    })

    let resolveProbe: (value: { connected: boolean; connectionType: 'wifi' }) => void = () => {}
    getStatus.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveProbe = resolve
        }),
    )
    act(() => {
      for (const onForeground of appForegroundListeners.current) {
        onForeground()
      }
    })
    act(() => {
      listener?.({ connected: false })
    })
    await act(async () => {
      resolveProbe({ connected: true, connectionType: 'wifi' })
      await Promise.resolve()
    })

    expect(result.current.isOnline).toBe(false)
    expect(onlineManager.isOnline()).toBe(false)
    expect(onOnline).not.toHaveBeenCalled()
    unsubscribe()
  })

  it('keeps the snapshot when foreground getStatus rejects', async () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    isNativePlatform.mockReturnValue(true)
    getStatus.mockResolvedValue({ connected: true, connectionType: 'wifi' })
    let listener: ((status: { connected: boolean }) => void) | undefined
    addListener.mockImplementation(async (_event, next) => {
      listener = next
      return { remove: async () => undefined }
    })

    await configureNativeNetworkStatus()
    const { result } = renderHook(() => useNetworkStatus())
    const onOnline = vi.fn()
    const unsubscribe = subscribeNetworkOnline(onOnline)

    act(() => {
      listener?.({ connected: false })
    })
    expect(onlineManager.isOnline()).toBe(false)

    getStatus.mockRejectedValueOnce(new Error('status'))
    await act(async () => {
      for (const onForeground of appForegroundListeners.current) {
        onForeground()
      }
      await Promise.resolve()
    })

    expect(result.current.isOnline).toBe(false)
    expect(onlineManager.isOnline()).toBe(false)
    expect(onOnline).not.toHaveBeenCalled()
    unsubscribe()
  })

  it('does not arm a retry when getStatus rejects', async () => {
    vi.useFakeTimers()
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    isNativePlatform.mockReturnValue(true)
    getStatus.mockResolvedValue({ connected: true, connectionType: 'wifi' })
    let listener: ((status: { connected: boolean }) => void) | undefined
    addListener.mockImplementation(async (_event, next) => {
      listener = next
      return { remove: async () => undefined }
    })

    await configureNativeNetworkStatus()
    act(() => {
      listener?.({ connected: false })
    })

    getStatus.mockReset()
    getStatus.mockRejectedValueOnce(new Error('status'))
    await act(async () => {
      for (const onForeground of appForegroundListeners.current) {
        onForeground()
      }
      await Promise.resolve()
    })
    expect(getStatus).toHaveBeenCalledTimes(1)

    getStatus.mockClear()
    getStatus.mockResolvedValue({ connected: true, connectionType: 'wifi' })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000)
    })
    expect(getStatus).not.toHaveBeenCalled()
    expect(getIsOnline()).toBe(false)
    expect(onlineManager.isOnline()).toBe(false)
  })

  it('does not apply a retry after the app goes to background', async () => {
    vi.useFakeTimers()
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    isNativePlatform.mockReturnValue(true)
    getStatus.mockResolvedValue({ connected: true, connectionType: 'wifi' })
    let listener: ((status: { connected: boolean }) => void) | undefined
    addListener.mockImplementation(async (_event, next) => {
      listener = next
      return { remove: async () => undefined }
    })

    await configureNativeNetworkStatus()
    const onOnline = vi.fn()
    const unsubscribe = subscribeNetworkOnline(onOnline)
    act(() => {
      listener?.({ connected: false })
    })

    getStatus.mockReset()
    getStatus.mockResolvedValueOnce({ connected: false, connectionType: 'wifi' })
    await act(async () => {
      for (const onForeground of appForegroundListeners.current) {
        onForeground()
      }
      await Promise.resolve()
    })

    isAppActive.current = false
    act(() => {
      for (const onBackground of appBackgroundListeners.current) {
        onBackground()
      }
    })

    getStatus.mockClear()
    getStatus.mockResolvedValue({ connected: true, connectionType: 'wifi' })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000)
    })

    expect(getStatus).not.toHaveBeenCalled()
    expect(getIsOnline()).toBe(false)
    expect(onlineManager.isOnline()).toBe(false)
    expect(onOnline).not.toHaveBeenCalled()
    unsubscribe()
  })

  it('does not apply a retry after a newer networkStatusChange', async () => {
    vi.useFakeTimers()
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    isNativePlatform.mockReturnValue(true)
    getStatus.mockResolvedValue({ connected: true, connectionType: 'wifi' })
    let listener: ((status: { connected: boolean }) => void) | undefined
    addListener.mockImplementation(async (_event, next) => {
      listener = next
      return { remove: async () => undefined }
    })

    await configureNativeNetworkStatus()
    act(() => {
      listener?.({ connected: false })
    })

    getStatus.mockReset()
    getStatus.mockResolvedValueOnce({ connected: false, connectionType: 'wifi' })
    await act(async () => {
      for (const onForeground of appForegroundListeners.current) {
        onForeground()
      }
      await Promise.resolve()
    })

    act(() => {
      listener?.({ connected: false })
    })

    getStatus.mockClear()
    getStatus.mockResolvedValue({ connected: true, connectionType: 'wifi' })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000)
    })

    expect(getStatus).not.toHaveBeenCalled()
    expect(getIsOnline()).toBe(false)
    expect(onlineManager.isOnline()).toBe(false)
  })
})
