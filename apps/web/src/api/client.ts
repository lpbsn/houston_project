import createClient from 'openapi-fetch'

import type { paths } from './types'

export const apiClient = createClient<paths>({
  baseUrl: '',
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
    authRuntime.clearAuth()
    return result
  }

  const retriedResult = await execute(refreshedToken)

  if (retriedResult.response.status === 401) {
    authRuntime.clearAuth()
  }

  return retriedResult
}
