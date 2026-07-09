import { describe, expect, it } from 'vitest'

import {
  getPushToggleMessage,
  resolvePushToggleState,
  type PushSupportEnvironment,
} from './support'

const baseEnv: PushSupportEnvironment = {
  isIosDevice: false,
  isStandalonePwa: false,
  hasServiceWorker: true,
  hasPushManager: true,
  hasNotification: true,
  permission: 'default',
}

describe('resolvePushToggleState', () => {
  it('returns ios_not_installed before unsupported on iOS Safari', () => {
    const env: PushSupportEnvironment = {
      ...baseEnv,
      isIosDevice: true,
      isStandalonePwa: false,
      hasPushManager: false,
      hasServiceWorker: false,
      hasNotification: false,
    }

    expect(resolvePushToggleState({ env, pushEnabled: false, hasLocalSubscription: false })).toBe(
      'ios_not_installed',
    )
  })

  it('returns unsupported when APIs are missing outside iOS non-PWA', () => {
    const env: PushSupportEnvironment = {
      ...baseEnv,
      hasPushManager: false,
    }

    expect(resolvePushToggleState({ env, pushEnabled: false, hasLocalSubscription: false })).toBe(
      'unsupported',
    )
  })

  it('returns permission_denied when browser permission is denied', () => {
    const env: PushSupportEnvironment = {
      ...baseEnv,
      permission: 'denied',
    }

    expect(resolvePushToggleState({ env, pushEnabled: true, hasLocalSubscription: true })).toBe(
      'permission_denied',
    )
  })

  it('returns enabled only when push_enabled, permission granted, and local subscription exist', () => {
    const env: PushSupportEnvironment = {
      ...baseEnv,
      permission: 'granted',
    }

    expect(resolvePushToggleState({ env, pushEnabled: true, hasLocalSubscription: true })).toBe(
      'enabled',
    )
    expect(resolvePushToggleState({ env, pushEnabled: true, hasLocalSubscription: false })).toBe(
      'disabled',
    )
    expect(resolvePushToggleState({ env, pushEnabled: false, hasLocalSubscription: true })).toBe(
      'disabled',
    )
  })

  it('returns disabled for default permission without local subscription', () => {
    expect(
      resolvePushToggleState({
        env: baseEnv,
        pushEnabled: false,
        hasLocalSubscription: false,
      }),
    ).toBe('disabled')
  })
})

describe('getPushToggleMessage', () => {
  it('returns explicit UX messages for blocked states', () => {
    expect(getPushToggleMessage('unsupported')).toContain('pas disponibles')
    expect(getPushToggleMessage('ios_not_installed')).toContain('écran d')
    expect(getPushToggleMessage('permission_denied')).toContain('bloquées')
    expect(getPushToggleMessage('enabled')).toBeNull()
    expect(getPushToggleMessage('disabled')).toBeNull()
  })
})
