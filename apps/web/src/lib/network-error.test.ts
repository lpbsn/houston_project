import { describe, expect, it } from 'vitest'

import { SignalsApiError } from '@/features/signals/api'

import {
  isNetworkFailure,
  NETWORK_FAILURE_MESSAGE,
  OFFLINE_BANNER_MESSAGE,
} from './network-error'

describe('network-error', () => {
  it('exports field-friendly copy constants', () => {
    expect(NETWORK_FAILURE_MESSAGE.length).toBeGreaterThan(0)
    expect(OFFLINE_BANNER_MESSAGE.length).toBeGreaterThan(0)
  })

  it('detects fetch TypeError failures', () => {
    expect(isNetworkFailure(new TypeError('Failed to fetch'))).toBe(true)
    expect(isNetworkFailure(new TypeError('NetworkError when attempting to fetch resource.'))).toBe(
      true,
    )
    expect(isNetworkFailure(new TypeError('Load failed'))).toBe(true)
  })

  it('detects DOMException network failures', () => {
    expect(isNetworkFailure(new DOMException('NetworkError', 'NetworkError'))).toBe(true)
  })

  it('does not treat HTTP API errors as network failures', () => {
    expect(
      isNetworkFailure(
        new SignalsApiError({ status: 500, detail: 'Erreur serveur.', code: 'server_error' }),
      ),
    ).toBe(false)
    expect(isNetworkFailure({ status: 503, detail: 'Unavailable' })).toBe(false)
  })

  it('does not treat unrelated TypeErrors as network failures', () => {
    expect(isNetworkFailure(new TypeError('Cannot read properties of undefined'))).toBe(false)
  })
})
