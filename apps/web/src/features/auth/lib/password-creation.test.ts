import { describe, expect, it } from 'vitest'

import {
  PASSWORD_MIN_LENGTH,
  canSubmitPasswordCreation,
  evaluatePasswordCreation,
  passwordCreationBlockerMessage,
} from './password-creation'

describe('password creation local checks', () => {
  it('exports the Django minimum length', () => {
    expect(PASSWORD_MIN_LENGTH).toBe(12)
  })

  it('flags short, numeric-only, and mismatched passwords', () => {
    expect(evaluatePasswordCreation('short', 'short')).toEqual({
      empty: false,
      tooShort: true,
      numericOnly: false,
      mismatch: false,
    })
    expect(evaluatePasswordCreation('123456789012', '123456789012')).toMatchObject({
      numericOnly: true,
      tooShort: false,
    })
    expect(evaluatePasswordCreation('StrongPass123!', 'other-pass-12')).toMatchObject({
      mismatch: true,
    })
  })

  it('allows submit only when local trivial rules pass', () => {
    expect(canSubmitPasswordCreation('StrongPass123!', 'StrongPass123!')).toBe(true)
    expect(canSubmitPasswordCreation('short', 'short')).toBe(false)
    expect(canSubmitPasswordCreation('StrongPass123!', 'mismatch1234')).toBe(false)
    expect(passwordCreationBlockerMessage(evaluatePasswordCreation('123456789012', '123456789012'))).toBeTruthy()
  })
})
