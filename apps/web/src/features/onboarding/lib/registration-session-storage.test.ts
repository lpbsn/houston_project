// @vitest-environment jsdom

import { afterEach, describe, expect, it } from 'vitest'

import {
  REGISTRATION_SESSION_STORAGE_KEY,
  clearRegistrationSessionSnapshot,
  loadRegistrationSessionSnapshot,
  saveRegistrationSessionSnapshot,
} from './registration-session-storage'

afterEach(() => {
  window.sessionStorage.clear()
})

describe('registration-session-storage', () => {
  it('round-trips non-secret fields', () => {
    saveRegistrationSessionSnapshot({
      invite_code: 'code',
      first_name: 'Alex',
      last_name: 'Owner',
      email: 'alex@example.com',
      organization_name: 'Northwind',
    })

    expect(loadRegistrationSessionSnapshot()).toEqual({
      invite_code: 'code',
      first_name: 'Alex',
      last_name: 'Owner',
      email: 'alex@example.com',
      organization_name: 'Northwind',
    })
  })

  it('ignores corrupted JSON', () => {
    window.sessionStorage.setItem(REGISTRATION_SESSION_STORAGE_KEY, '{not-json')
    expect(loadRegistrationSessionSnapshot()).toEqual({
      invite_code: '',
      first_name: '',
      last_name: '',
      email: '',
      organization_name: '',
    })
  })

  it('ignores unexpected shape and secret keys', () => {
    window.sessionStorage.setItem(
      REGISTRATION_SESSION_STORAGE_KEY,
      JSON.stringify({
        invite_code: 'code',
        first_name: 'Alex',
        last_name: 'Owner',
        email: 'alex@example.com',
        organization_name: 'Northwind',
        password: 'secret',
      }),
    )
    expect(loadRegistrationSessionSnapshot().invite_code).toBe('')
  })

  it('clears stored snapshot', () => {
    saveRegistrationSessionSnapshot({
      invite_code: 'code',
      first_name: 'Alex',
      last_name: 'Owner',
      email: 'alex@example.com',
      organization_name: 'Northwind',
    })
    clearRegistrationSessionSnapshot()
    expect(window.sessionStorage.getItem(REGISTRATION_SESSION_STORAGE_KEY)).toBeNull()
  })

  it('never writes passwords when saving', () => {
    saveRegistrationSessionSnapshot({
      invite_code: 'code',
      first_name: 'Alex',
      last_name: 'Owner',
      email: 'alex@example.com',
      organization_name: 'Northwind',
    })
    const raw = window.sessionStorage.getItem(REGISTRATION_SESSION_STORAGE_KEY) ?? ''
    expect(raw).not.toContain('password')
  })
})
