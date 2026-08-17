import { afterEach, describe, expect, it, vi } from 'vitest'

const isNativePlatform = vi.hoisted(() => vi.fn(() => false))
const setSynchronize = vi.hoisted(() => vi.fn(async () => undefined))
const setKeyPrefix = vi.hoisted(() => vi.fn(async () => undefined))
const getStored = vi.hoisted(() => vi.fn(async () => null))
const setStored = vi.hoisted(() => vi.fn(async () => undefined))
const removeStored = vi.hoisted(() => vi.fn(async () => true))

vi.mock('@capacitor/core', () => ({
  Capacitor: {
    isNativePlatform: () => isNativePlatform(),
  },
}))

vi.mock('@aparajita/capacitor-secure-storage', () => ({
  SecureStorage: {
    setSynchronize: (...args: unknown[]) => setSynchronize(...args),
    setKeyPrefix: (...args: unknown[]) => setKeyPrefix(...args),
    get: (...args: unknown[]) => getStored(...args),
    set: (...args: unknown[]) => setStored(...args),
    remove: (...args: unknown[]) => removeStored(...args),
  },
}))

import {
  clearBodyRefreshTokenStoreConfiguration,
  clearPersistedRefreshToken,
  persistRefreshFromAuthResponse,
  prepareRefreshTransport,
} from './refresh-token-transport'
import { configureNativeBodyRefreshTokenStore } from './native-refresh-token-store'

describe('native body refresh token store', () => {
  afterEach(() => {
    clearBodyRefreshTokenStoreConfiguration()
    isNativePlatform.mockReset()
    isNativePlatform.mockReturnValue(false)
    setSynchronize.mockClear()
    setKeyPrefix.mockClear()
    getStored.mockReset()
    setStored.mockClear()
    removeStored.mockClear()
    vi.unstubAllEnvs()
  })

  it('does not configure storage for a native Vite build running off-device', async () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    isNativePlatform.mockReturnValue(false)

    await configureNativeBodyRefreshTokenStore()

    expect(setSynchronize).not.toHaveBeenCalled()
    await expect(prepareRefreshTransport()).rejects.toThrow(/not configured/)
  })

  it('does not configure storage in web runtime even on a native platform', async () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'web')
    isNativePlatform.mockReturnValue(true)

    await configureNativeBodyRefreshTokenStore()

    expect(isNativePlatform).not.toHaveBeenCalled()
    expect(setSynchronize).not.toHaveBeenCalled()
  })

  it('wires Keychain storage with iCloud sync disabled', async () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    isNativePlatform.mockReturnValue(true)
    getStored.mockResolvedValue({
      token: 'native-refresh',
      expiresAt: '2026-09-15T00:00:00Z',
    })

    await configureNativeBodyRefreshTokenStore()

    expect(setSynchronize).toHaveBeenCalledWith(false)
    expect(setKeyPrefix).toHaveBeenCalledWith('houston-auth_')
    await expect(prepareRefreshTransport()).resolves.toEqual({
      transport: 'body',
      credentials: 'omit',
      refreshToken: 'native-refresh',
    })
    expect(getStored).toHaveBeenCalledWith('refresh_token', false, false)

    await persistRefreshFromAuthResponse({
      refresh_token: 'rotated-native-refresh',
      refresh_token_expires_at: '2026-09-16T00:00:00Z',
    })
    expect(setStored).toHaveBeenCalledWith(
      'refresh_token',
      { token: 'rotated-native-refresh', expiresAt: '2026-09-16T00:00:00Z' },
      false,
      false,
    )

    await clearPersistedRefreshToken()
    expect(removeStored).toHaveBeenCalledWith('refresh_token', false)
  })
})
