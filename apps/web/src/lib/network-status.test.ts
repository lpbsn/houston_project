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

import {
  configureNativeNetworkStatus,
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
})
