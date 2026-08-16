export type AppRuntime = 'web' | 'native'

function trimTrailingSlash(value: string): string {
  return value.replace(/\/+$/, '')
}

function readApiBaseUrl(): string {
  return trimTrailingSlash((import.meta.env.VITE_API_BASE_URL ?? '').trim())
}

export function getAppRuntime(): AppRuntime {
  return import.meta.env.VITE_APP_RUNTIME === 'native' ? 'native' : 'web'
}

export function getApiBaseUrl(): string {
  const baseUrl = readApiBaseUrl()
  if (getAppRuntime() === 'native' && !baseUrl) {
    throw new Error('VITE_API_BASE_URL is required when VITE_APP_RUNTIME=native.')
  }
  return baseUrl
}

export function resolveApiUrl(path: string): string {
  if (/^[a-z][a-z0-9+.-]*:/i.test(path)) {
    return path
  }
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return `${getApiBaseUrl()}${normalizedPath}`
}

export function resolveWsUrl(path: string): string {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  const apiBase = getApiBaseUrl()
  if (apiBase) {
    const wsBase = apiBase.replace(/^http:/i, 'ws:').replace(/^https:/i, 'wss:')
    return `${wsBase}${normalizedPath}`
  }
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}${normalizedPath}`
}
