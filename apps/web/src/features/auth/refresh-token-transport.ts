import { getAppRuntime } from '@/lib/runtime'

import { ensureCsrfToken } from './csrf'

export type RefreshTokenTransport = 'cookie' | 'body'

export type StoredRefreshToken = {
  token: string
  expiresAt: string
}

export type BodyRefreshTokenStore = {
  read: () => Promise<StoredRefreshToken | null>
  write: (value: StoredRefreshToken) => Promise<void>
  clear: () => Promise<void>
}

export type PreparedAuthTransport = {
  transport: RefreshTokenTransport
  credentials: RequestCredentials
  csrfToken?: string
  refreshToken?: string
}

type AuthResponseWithRefresh = {
  refresh_token?: string
  refresh_token_expires_at?: string
}

let bodyRefreshTokenStore: BodyRefreshTokenStore | null = null

export function configureBodyRefreshTokenStore(store: BodyRefreshTokenStore) {
  bodyRefreshTokenStore = store
}

export function clearBodyRefreshTokenStoreConfiguration() {
  bodyRefreshTokenStore = null
}

export function getRefreshTokenTransport(): RefreshTokenTransport {
  return getAppRuntime() === 'native' ? 'body' : 'cookie'
}

export async function prepareSessionCreationTransport(): Promise<PreparedAuthTransport> {
  if (getRefreshTokenTransport() === 'body') {
    return { transport: 'body', credentials: 'omit' }
  }

  return {
    transport: 'cookie',
    credentials: 'include',
    csrfToken: await ensureCsrfToken(),
  }
}

export async function prepareRefreshTransport(): Promise<PreparedAuthTransport> {
  const prepared = await prepareSessionCreationTransport()
  if (prepared.transport === 'cookie') {
    return prepared
  }

  const stored = await requireBodyStore().read()
  if (!stored?.token) {
    throw new Error('No persisted refresh token is available.')
  }
  return { ...prepared, refreshToken: stored.token }
}

export async function prepareLogoutTransport(options: {
  hasBearer: boolean
}): Promise<PreparedAuthTransport> {
  const prepared = await prepareSessionCreationTransport()
  if (prepared.transport === 'cookie' || options.hasBearer) {
    return prepared
  }

  const stored = await requireBodyStore().read()
  return { ...prepared, refreshToken: stored?.token }
}

export async function persistRefreshFromAuthResponse(payload: AuthResponseWithRefresh) {
  if (getRefreshTokenTransport() === 'cookie') {
    return
  }

  if (!payload.refresh_token || !payload.refresh_token_expires_at) {
    throw new Error('The body auth response did not include a refresh token.')
  }

  await requireBodyStore().write({
    token: payload.refresh_token,
    expiresAt: payload.refresh_token_expires_at,
  })
}

export async function clearPersistedRefreshToken() {
  if (getRefreshTokenTransport() === 'body' && bodyRefreshTokenStore) {
    await bodyRefreshTokenStore.clear()
  }
}

function requireBodyStore() {
  if (!bodyRefreshTokenStore) {
    throw new Error('Body refresh token storage is not configured.')
  }
  return bodyRefreshTokenStore
}
