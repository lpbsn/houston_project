export type AppRuntime = 'web' | 'native'

const LOOPBACK_HOSTNAMES = new Set(['localhost', '127.0.0.1'])

function trimTrailingSlash(value: string): string {
  return value.replace(/\/+$/, '')
}

function readApiBaseUrl(): string {
  return trimTrailingSlash((import.meta.env.VITE_API_BASE_URL ?? '').trim())
}

function normalizeWebLoopbackApiBaseUrl(baseUrl: string): string {
  if (!baseUrl || typeof window === 'undefined') {
    return baseUrl
  }

  const pageHostname = window.location.hostname
  if (!LOOPBACK_HOSTNAMES.has(pageHostname)) {
    return baseUrl
  }

  let apiUrl: URL
  try {
    apiUrl = new URL(baseUrl)
  } catch {
    return baseUrl
  }
  if (!LOOPBACK_HOSTNAMES.has(apiUrl.hostname) || apiUrl.hostname === pageHostname) {
    return baseUrl
  }

  apiUrl.hostname = pageHostname
  return trimTrailingSlash(apiUrl.toString())
}

export function getAppRuntime(): AppRuntime {
  return import.meta.env.VITE_APP_RUNTIME === 'native' ? 'native' : 'web'
}

export function getApiBaseUrl(): string {
  const baseUrl = readApiBaseUrl()
  const runtime = getAppRuntime()
  if (runtime === 'native' && !baseUrl) {
    throw new Error('VITE_API_BASE_URL is required when VITE_APP_RUNTIME=native.')
  }
  return runtime === 'web' ? normalizeWebLoopbackApiBaseUrl(baseUrl) : baseUrl
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
