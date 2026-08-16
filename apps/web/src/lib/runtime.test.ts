// @vitest-environment jsdom

import { afterEach, describe, expect, it, vi } from 'vitest'

import { getApiBaseUrl, getAppRuntime, resolveApiUrl, resolveWsUrl } from './runtime'

describe('runtime', () => {
  afterEach(() => {
    vi.unstubAllEnvs()
    vi.unstubAllGlobals()
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
    vi.stubEnv('VITE_APP_RUNTIME', 'web')
    vi.stubEnv('VITE_API_BASE_URL', '')
    vi.stubGlobal('window', { location: { hostname: '127.0.0.1' } })

    expect(getApiBaseUrl()).toBe('')
    expect(resolveApiUrl('/api/v1/auth/csrf/')).toBe('/api/v1/auth/csrf/')
  })

  it('aligns a localhost API with a 127.0.0.1 web page', () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'web')
    vi.stubEnv('VITE_API_BASE_URL', 'http://localhost:8000/base/')
    vi.stubGlobal('window', { location: { hostname: '127.0.0.1' } })

    expect(getApiBaseUrl()).toBe('http://127.0.0.1:8000/base')
    expect(resolveApiUrl('/api/v1/auth/csrf/')).toBe(
      'http://127.0.0.1:8000/base/api/v1/auth/csrf/',
    )
  })

  it('aligns a 127.0.0.1 API with a localhost web page', () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'web')
    vi.stubEnv('VITE_API_BASE_URL', 'http://127.0.0.1:8000')
    vi.stubGlobal('window', { location: { hostname: 'localhost' } })

    expect(getApiBaseUrl()).toBe('http://localhost:8000')
  })

  it('leaves a remote API unchanged in web runtime', () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'web')
    vi.stubEnv('VITE_API_BASE_URL', 'https://api.example.test')
    vi.stubGlobal('window', { location: { hostname: '127.0.0.1' } })

    expect(getApiBaseUrl()).toBe('https://api.example.test')
  })

  it('leaves a loopback API unchanged in native runtime', () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    vi.stubEnv('VITE_API_BASE_URL', 'http://localhost:8000')
    vi.stubGlobal('window', { location: { hostname: '127.0.0.1' } })

    expect(getApiBaseUrl()).toBe('http://localhost:8000')
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
