import createClient from 'openapi-fetch'

import { getApiBaseUrl, resolveApiUrl } from '@/lib/runtime'

import type { paths } from "./generated/types"

export const apiClient = createClient<paths>({
  baseUrl: getApiBaseUrl(),
})

type AuthRuntime = {
  getAccessToken: () => string | null
  refreshAccessToken: () => Promise<string | null>
  clearAuth: () => void
}

let authRuntime: AuthRuntime | null = null

export function configureApiClientAuth(runtime: AuthRuntime) {
  authRuntime = runtime
}

export function clearApiClientAuth() {
  authRuntime = null
}

export async function withAuthRetry<TResult extends { response: Response }>(
  execute: (accessToken: string | null) => Promise<TResult>,
  options: { refreshable?: boolean } = {},
) {
  const initialToken = authRuntime?.getAccessToken() ?? null
  const result = await execute(initialToken)

  if (
    options.refreshable === false ||
    result.response.status !== 401 ||
    !authRuntime ||
    !initialToken
  ) {
    return result
  }

  const refreshedToken = await authRuntime.refreshAccessToken()

  if (!refreshedToken) {
    if (authRuntime.getAccessToken() === initialToken) {
      authRuntime.clearAuth()
    }
    return result
  }

  const retriedResult = await execute(refreshedToken)

  if (
    retriedResult.response.status === 401 &&
    authRuntime.getAccessToken() === refreshedToken
  ) {
    authRuntime.clearAuth()
  }

  return retriedResult
}

function resolveFetchInput(input: RequestInfo | URL): RequestInfo | URL {
  if (typeof input === 'string') {
    return resolveApiUrl(input)
  }
  return input
}

export async function fetchWithAuthRetry(
  input: RequestInfo | URL,
  init: RequestInit,
): Promise<Response> {
  const result = await withAuthRetry(async (token) => {
    const headers = new Headers(init.headers)
    if (token) {
      headers.set('Authorization', `Bearer ${token}`)
    } else {
      headers.delete('Authorization')
    }
    const response = await fetch(resolveFetchInput(input), { ...init, headers })
    return { response }
  })
  return result.response
}
