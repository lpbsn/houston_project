import type { SecureStoragePlugin } from '@aparajita/capacitor-secure-storage'

import { getAppRuntime } from '@/lib/runtime'

import {
  configureBodyRefreshTokenStore,
  type BodyRefreshTokenStore,
  type StoredRefreshToken,
} from './refresh-token-transport'

const STORAGE_KEY = 'refresh_token'
const KEY_PREFIX = 'houston-auth_'

function parseStoredRefreshToken(value: unknown): StoredRefreshToken | null {
  if (typeof value !== 'object' || value === null) {
    return null
  }

  const token = 'token' in value ? value.token : null
  const expiresAt = 'expiresAt' in value ? value.expiresAt : null
  if (typeof token !== 'string' || token.length === 0 || typeof expiresAt !== 'string') {
    return null
  }

  return { token, expiresAt }
}

function createNativeBodyRefreshTokenStore(storage: SecureStoragePlugin): BodyRefreshTokenStore {
  return {
    async read() {
      const value = await storage.get(STORAGE_KEY, false, false)
      return parseStoredRefreshToken(value)
    },
    async write(value) {
      await storage.set(STORAGE_KEY, value, false, false)
    },
    async clear() {
      await storage.remove(STORAGE_KEY, false)
    },
  }
}

export async function configureNativeBodyRefreshTokenStore() {
  if (getAppRuntime() !== 'native') {
    return
  }

  const { Capacitor } = await import('@capacitor/core')
  if (!Capacitor.isNativePlatform()) {
    return
  }

  const { SecureStorage } = await import('@aparajita/capacitor-secure-storage')
  await SecureStorage.setSynchronize(false)
  await SecureStorage.setKeyPrefix(KEY_PREFIX)
  configureBodyRefreshTokenStore(createNativeBodyRefreshTokenStore(SecureStorage))
}
