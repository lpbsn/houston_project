// @vitest-environment jsdom

import { afterEach, describe, expect, it, vi } from 'vitest'

import { getApiBaseUrl, getAppRuntime, resolveApiUrl, resolveWsUrl } from './runtime'

describe('runtime', () => {
  afterEach(() => {
    vi.unstubAllEnvs()
  })

  it('defaults the runtime to web', () => {
    expect(getAppRuntime()).toBe('web')
  })

  it('reads an explicit native runtime', () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    vi.stubEnv('VITE_API_BASE_URL', 'https://api.example.test')

    expect(getAppRuntime()).toBe('native')
  })

  it('treats an empty API base as same-origin', () => {
    vi.stubEnv('VITE_API_BASE_URL', '')

    expect(getApiBaseUrl()).toBe('')
    expect(resolveApiUrl('/api/v1/auth/csrf/')).toBe('/api/v1/auth/csrf/')
  })

  it('strips a trailing slash from an absolute API base', () => {
    vi.stubEnv('VITE_API_BASE_URL', 'http://localhost:8000/')

    expect(getApiBaseUrl()).toBe('http://localhost:8000')
    expect(resolveApiUrl('/api/v1/auth/csrf/')).toBe('http://localhost:8000/api/v1/auth/csrf/')
  })

  it('throws when native runtime has no API base URL', () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    vi.stubEnv('VITE_API_BASE_URL', '')

    expect(() => getApiBaseUrl()).toThrow(/VITE_API_BASE_URL is required/)
  })

  it('derives the WebSocket host from an absolute API base', () => {
    vi.stubEnv('VITE_API_BASE_URL', 'https://api.example.test')

    expect(resolveWsUrl('/ws/v1/establishments/est-1/chat/')).toBe(
      'wss://api.example.test/ws/v1/establishments/est-1/chat/',
    )
  })

  it('uses the current window location when the API base is empty', () => {
    vi.stubEnv('VITE_API_BASE_URL', '')

    expect(resolveWsUrl('/ws/v1/establishments/est-1/realtime/')).toBe(
      `ws://${window.location.host}/ws/v1/establishments/est-1/realtime/`,
    )
  })
})
