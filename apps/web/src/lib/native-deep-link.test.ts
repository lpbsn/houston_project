// @vitest-environment jsdom

import { afterEach, describe, expect, it, vi } from 'vitest'

const isNativePlatform = vi.hoisted(() => vi.fn(() => false))
const getLaunchUrl = vi.hoisted(() => vi.fn(async () => ({ url: undefined as string | undefined })))
const addListener = vi.hoisted(() =>
  vi.fn(async (event: string, cb: (payload: { url: string }) => void) => {
    listeners[event] = cb
    return { remove: async () => undefined }
  }),
)
const listeners: Record<string, ((payload: { url: string }) => void) | undefined> = {}
const switchEstablishment = vi.hoisted(() => vi.fn(async () => undefined))

vi.mock('@capacitor/core', () => ({
  Capacitor: {
    isNativePlatform: () => isNativePlatform(),
  },
}))

vi.mock('@capacitor/app', () => ({
  App: {
    getLaunchUrl: () => getLaunchUrl(),
    addListener: (...args: unknown[]) =>
      addListener(...(args as [string, (payload: { url: string }) => void])),
  },
}))

vi.mock('@/features/auth/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/features/auth/api')>()
  return {
    ...actual,
    switchEstablishment: (...args: unknown[]) => switchEstablishment(...args),
  }
})

import { createMemoryHistory } from '@/app/app-history'
import { AuthApiError, bootstrapQueryKey } from '@/features/auth/api'
import { queryClient } from '@/lib/query-client'
import {
  applyPendingNativeDeepLink,
  clearPendingNativeDeepLink,
  peekPendingNativeDeepLink,
  setNativeDeepLinkSessionGetters,
} from './native-deep-link-session'
import { configureNativeDeepLinks, resetNativeDeepLinksForTests } from './native-deep-link'
import { setNativePushActiveEstablishmentGetter } from './native-push-session'

const PUBLIC_ORIGIN = 'https://app.example.test'
const SIGNAL_URL = `${PUBLIC_ORIGIN}/signals/s1?establishment_id=est-2`
const CHAT_URL = `${PUBLIC_ORIGIN}/chat/c1`

describe('native deep links', () => {
  afterEach(async () => {
    await resetNativeDeepLinksForTests()
    isNativePlatform.mockReturnValue(false)
    getLaunchUrl.mockReset()
    getLaunchUrl.mockResolvedValue({ url: undefined })
    addListener.mockClear()
    switchEstablishment.mockReset()
    listeners.appUrlOpen = undefined
    queryClient.removeQueries({ queryKey: bootstrapQueryKey })
    vi.unstubAllEnvs()
  })

  async function configure(history = createMemoryHistory('/')) {
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    vi.stubEnv('VITE_PUBLIC_APP_URL', PUBLIC_ORIGIN)
    isNativePlatform.mockReturnValue(true)
    await configureNativeDeepLinks({ history })
    return history
  }

  it('holds a cold-start launch URL until session is ready then resumes with establishment_id', async () => {
    getLaunchUrl.mockResolvedValue({ url: SIGNAL_URL })
    const history = await configure(createMemoryHistory('/profile'))

    expect(peekPendingNativeDeepLink()).toEqual({
      href: '/signals/s1',
      establishmentId: 'est-2',
    })
    expect(history.getHref()).toBe('/profile')

    setNativeDeepLinkSessionGetters({
      isReady: () => true,
      isAuthenticated: () => false,
    })
    await applyPendingNativeDeepLink()

    const href = history.getHref()
    expect(href.startsWith('/login?')).toBe(true)
    expect(href).toContain('next=%2Fsignals%2Fs1')
    expect(href).toContain('establishment_id=est-2')
    expect(peekPendingNativeDeepLink()).toBeNull()
  })

  it('navigates a warm authenticated open and switches when the hint differs', async () => {
    const history = await configure()
    setNativePushActiveEstablishmentGetter(() => 'est-1')
    setNativeDeepLinkSessionGetters({
      isReady: () => true,
      isAuthenticated: () => true,
    })

    listeners.appUrlOpen?.({ url: SIGNAL_URL })
    await vi.waitFor(() => {
      expect(switchEstablishment).toHaveBeenCalledWith({ establishment_id: 'est-2' })
      expect(history.getHref()).toBe('/signals/s1')
    })
  })

  it('dedupes getLaunchUrl and a synchronous handshake appUrlOpen only', async () => {
    getLaunchUrl.mockResolvedValue({ url: SIGNAL_URL })
    addListener.mockImplementationOnce(async (event, cb) => {
      listeners[event] = cb
      if (event === 'appUrlOpen') {
        cb({ url: SIGNAL_URL })
      }
      return { remove: async () => undefined }
    })
    const history = await configure()
    setNativeDeepLinkSessionGetters({
      isReady: () => true,
      isAuthenticated: () => true,
    })
    setNativePushActiveEstablishmentGetter(() => 'est-2')
    await applyPendingNativeDeepLink()
    expect(history.getHref()).toBe('/signals/s1')
    expect(switchEstablishment).not.toHaveBeenCalled()

    history.navigate('/reporting')
    listeners.appUrlOpen?.({ url: SIGNAL_URL })
    await vi.waitFor(() => {
      expect(history.getHref()).toBe('/signals/s1')
    })
  })

  it('applies a later open of the same href when cold start had no appUrlOpen duplicate', async () => {
    getLaunchUrl.mockResolvedValue({ url: SIGNAL_URL })
    const history = await configure(createMemoryHistory('/reporting'))
    setNativeDeepLinkSessionGetters({
      isReady: () => true,
      isAuthenticated: () => true,
    })
    setNativePushActiveEstablishmentGetter(() => 'est-2')
    await applyPendingNativeDeepLink()
    expect(history.getHref()).toBe('/signals/s1')

    history.navigate('/reporting')
    listeners.appUrlOpen?.({ url: SIGNAL_URL })
    await vi.waitFor(() => {
      expect(history.getHref()).toBe('/signals/s1')
    })
  })

  it('opens a public invitation without waiting for a session', async () => {
    getLaunchUrl.mockResolvedValue({ url: `${PUBLIC_ORIGIN}/invitations/token-abc` })
    const history = await configure()
    setNativeDeepLinkSessionGetters({
      isReady: () => true,
      isAuthenticated: () => false,
    })
    await applyPendingNativeDeepLink()
    expect(history.getHref()).toBe('/invitations/token-abc')
  })

  it('clears a pending open on demand', async () => {
    getLaunchUrl.mockResolvedValue({ url: SIGNAL_URL })
    await configure()
    expect(peekPendingNativeDeepLink()).not.toBeNull()
    clearPendingNativeDeepLink()
    expect(peekPendingNativeDeepLink()).toBeNull()
  })

  it('drains a concurrent open after the in-flight apply finishes', async () => {
    let resolveSwitch: () => void = () => undefined
    switchEstablishment.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveSwitch = () => resolve()
        }),
    )

    const history = await configure()
    setNativePushActiveEstablishmentGetter(() => 'est-1')
    setNativeDeepLinkSessionGetters({
      isReady: () => true,
      isAuthenticated: () => true,
    })

    listeners.appUrlOpen?.({ url: SIGNAL_URL })
    await vi.waitFor(() => {
      expect(switchEstablishment).toHaveBeenCalledWith({ establishment_id: 'est-2' })
    })

    listeners.appUrlOpen?.({ url: CHAT_URL })
    resolveSwitch()

    await vi.waitFor(() => {
      expect(history.getHref()).toBe('/chat/c1')
    })
  })

  it('navigates to landing and does not restore pending when switch is rejected', async () => {
    switchEstablishment.mockRejectedValueOnce(new AuthApiError('Not found.', 404))

    const history = await configure(createMemoryHistory('/profile'))
    setNativePushActiveEstablishmentGetter(() => 'est-1')
    setNativeDeepLinkSessionGetters({
      isReady: () => true,
      isAuthenticated: () => true,
    })

    listeners.appUrlOpen?.({ url: SIGNAL_URL })
    await vi.waitFor(() => {
      expect(history.getHref()).toBe('/reporting')
    })
    expect(peekPendingNativeDeepLink()).toBeNull()
    expect(history.getHref()).not.toBe('/signals/s1')
  })

  it('applies a concurrent open instead of landing when switch rejects', async () => {
    let rejectSwitch: (error: unknown) => void = () => undefined
    switchEstablishment.mockImplementationOnce(
      () =>
        new Promise((_, reject) => {
          rejectSwitch = reject
        }),
    )

    const history = await configure(createMemoryHistory('/profile'))
    setNativePushActiveEstablishmentGetter(() => 'est-1')
    setNativeDeepLinkSessionGetters({
      isReady: () => true,
      isAuthenticated: () => true,
    })

    listeners.appUrlOpen?.({ url: SIGNAL_URL })
    await vi.waitFor(() => {
      expect(switchEstablishment).toHaveBeenCalledWith({ establishment_id: 'est-2' })
    })

    listeners.appUrlOpen?.({ url: CHAT_URL })
    rejectSwitch(new AuthApiError('Not found.', 404))

    await vi.waitFor(() => {
      expect(history.getHref()).toBe('/chat/c1')
    })
    expect(peekPendingNativeDeepLink()).toBeNull()
  })
})
