import { describe, expect, it } from 'vitest'

import { SignalsApiError } from '@/features/signals/api'

import { resolveApiErrorMessage, toErrorMessage } from './error-message'
import { NETWORK_FAILURE_MESSAGE } from './network-error'

describe('error-message', () => {
  it('maps network failures to centralized copy in toErrorMessage', () => {
    expect(toErrorMessage(new TypeError('Failed to fetch'))).toBe(NETWORK_FAILURE_MESSAGE)
  })

  it('maps network failures before API error parsing in resolveApiErrorMessage', () => {
    expect(
      resolveApiErrorMessage(
        new TypeError('Failed to fetch'),
        SignalsApiError,
        'Une erreur est survenue.',
      ),
    ).toBe(NETWORK_FAILURE_MESSAGE)
  })

  it('preserves API error detail when not a network failure', () => {
    expect(
      resolveApiErrorMessage(
        new SignalsApiError({ status: 403, detail: 'Accès refusé.', code: 'forbidden' }),
        SignalsApiError,
        'Une erreur est survenue.',
      ),
    ).toBe('Accès refusé.')
  })

  it('falls back for unknown errors', () => {
    expect(resolveApiErrorMessage(null, SignalsApiError, 'Fallback.')).toBe('Fallback.')
  })
})
