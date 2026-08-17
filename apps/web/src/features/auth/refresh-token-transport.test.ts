import { afterEach, describe, expect, it, vi } from 'vitest'

const ensureCsrfToken = vi.hoisted(() => vi.fn(async () => 'csrf-token'))

vi.mock('./csrf', () => ({
  ensureCsrfToken,
}))

import {
  clearBodyRefreshTokenStoreConfiguration,
  clearPersistedRefreshToken,
  configureBodyRefreshTokenStore,
  persistRefreshFromAuthResponse,
  prepareLogoutTransport,
  prepareRefreshTransport,
  prepareSessionCreationTransport,
} from './refresh-token-transport'

describe('refresh token transport', () => {
  afterEach(() => {
    clearBodyRefreshTokenStoreConfiguration()
    ensureCsrfToken.mockClear()
    vi.unstubAllEnvs()
  })

  it('uses cookies, credentials and CSRF for web transport', async () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'web')

    await expect(prepareSessionCreationTransport()).resolves.toEqual({
      transport: 'cookie',
      credentials: 'include',
      csrfToken: 'csrf-token',
    })
    expect(ensureCsrfToken).toHaveBeenCalledOnce()
  })

  it('uses explicit storage and omits credentials for body transport', async () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    const store = {
      read: vi.fn(async () => ({ token: 'stored-refresh', expiresAt: '2026-09-01T00:00:00Z' })),
      write: vi.fn(async () => undefined),
      clear: vi.fn(async () => undefined),
    }
    configureBodyRefreshTokenStore(store)

    await expect(prepareRefreshTransport()).resolves.toEqual({
      transport: 'body',
      credentials: 'omit',
      refreshToken: 'stored-refresh',
    })
    await persistRefreshFromAuthResponse({
      refresh_token: 'rotated-refresh',
      refresh_token_expires_at: '2026-09-15T00:00:00Z',
    })
    await clearPersistedRefreshToken()

    expect(ensureCsrfToken).not.toHaveBeenCalled()
    expect(store.write).toHaveBeenCalledWith({
      token: 'rotated-refresh',
      expiresAt: '2026-09-15T00:00:00Z',
    })
    expect(store.clear).toHaveBeenCalledOnce()
  })

  it('attaches the stored refresh token for body logout', async () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    const store = {
      read: vi.fn(async () => ({ token: 'logout-refresh', expiresAt: '2026-09-01T00:00:00Z' })),
      write: vi.fn(async () => undefined),
      clear: vi.fn(async () => undefined),
    }
    configureBodyRefreshTokenStore(store)

    await expect(prepareLogoutTransport()).resolves.toEqual({
      transport: 'body',
      credentials: 'omit',
      refreshToken: 'logout-refresh',
    })
  })

  it('still prepares body logout when refresh storage is unavailable', async () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    const store = {
      read: vi.fn(async () => {
        throw new Error('secure store unavailable')
      }),
      write: vi.fn(async () => undefined),
      clear: vi.fn(async () => undefined),
    }
    configureBodyRefreshTokenStore(store)

    await expect(prepareLogoutTransport()).resolves.toEqual({
      transport: 'body',
      credentials: 'omit',
    })
  })
})
