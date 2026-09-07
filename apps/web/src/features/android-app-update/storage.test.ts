// @vitest-environment jsdom

import { afterEach, describe, expect, it } from 'vitest'

import { ANDROID_APP_UPDATE_STORAGE_KEY, SNOOZE_DURATION_MS } from './constants'
import {
  clearAndroidAppUpdateStateForTests,
  markAndroidAppUpdateChecked,
  readAndroidAppUpdateState,
  snoozeAndroidAppUpdate,
} from './storage'

describe('android app update storage', () => {
  afterEach(() => {
    clearAndroidAppUpdateStateForTests()
  })

  it('starts empty', () => {
    expect(readAndroidAppUpdateState()).toEqual({ lastCheckAtMs: null, snooze: null })
  })

  it('persists last check and a 24h snooze for the available version', () => {
    markAndroidAppUpdateChecked(1_000)
    snoozeAndroidAppUpdate('7', 1_000)
    expect(readAndroidAppUpdateState()).toEqual({
      lastCheckAtMs: 1_000,
      snooze: { availableVersionCode: '7', snoozedUntilMs: 1_000 + SNOOZE_DURATION_MS },
    })
    expect(window.localStorage.getItem(ANDROID_APP_UPDATE_STORAGE_KEY)).toContain('"7"')
  })

  it('ignores corrupt storage', () => {
    window.localStorage.setItem(ANDROID_APP_UPDATE_STORAGE_KEY, '{not-json')
    expect(readAndroidAppUpdateState()).toEqual({ lastCheckAtMs: null, snooze: null })
  })
})
