import { describe, expect, it } from 'vitest'

import { FOREGROUND_CHECK_INTERVAL_MS, PLAY_INSTALL_DOWNLOADED, PLAY_UPDATE_IN_PROGRESS } from './constants'
import {
  canUseAndroidInAppUpdates,
  decideAndroidAppUpdatePrompt,
  isAndroidVersionBelowMinimum,
  isPlayUpdateInstallable,
  isSnoozeActive,
  resolvePlayUpdateStartType,
  shouldCheckPlayOnForeground,
  type AndroidPlayUpdateSnapshot,
} from './rules'

function play(overrides: Partial<AndroidPlayUpdateSnapshot> = {}): AndroidPlayUpdateSnapshot {
  return {
    currentVersionCode: '2',
    availableVersionCode: '3',
    updateAvailability: 2,
    flexibleUpdateAllowed: true,
    immediateUpdateAllowed: true,
    installStatus: null,
    ...overrides,
  }
}

describe('android app update rules', () => {
  it('is Android-native only', () => {
    expect(
      canUseAndroidInAppUpdates({ runtime: 'native', isNativePlatform: true, platform: 'android' }),
    ).toBe(true)
    expect(
      canUseAndroidInAppUpdates({ runtime: 'native', isNativePlatform: true, platform: 'ios' }),
    ).toBe(false)
    expect(
      canUseAndroidInAppUpdates({ runtime: 'web', isNativePlatform: false, platform: 'web' }),
    ).toBe(false)
    expect(
      canUseAndroidInAppUpdates({ runtime: 'native', isNativePlatform: false, platform: 'android' }),
    ).toBe(false)
  })

  it('throttles foreground Play checks to 30 minutes', () => {
    expect(shouldCheckPlayOnForeground(null, 1000)).toBe(true)
    expect(shouldCheckPlayOnForeground(1_000, 1_000 + FOREGROUND_CHECK_INTERVAL_MS - 1)).toBe(false)
    expect(shouldCheckPlayOnForeground(1_000, 1_000 + FOREGROUND_CHECK_INTERVAL_MS)).toBe(true)
  })

  it('requires an installable Play update', () => {
    expect(isPlayUpdateInstallable(play())).toBe(true)
    expect(isPlayUpdateInstallable(play({ flexibleUpdateAllowed: false }))).toBe(true)
    expect(
      isPlayUpdateInstallable(
        play({ flexibleUpdateAllowed: false, immediateUpdateAllowed: false }),
      ),
    ).toBe(false)
    expect(isPlayUpdateInstallable(play({ updateAvailability: 1 }))).toBe(false)
  })

  it('compares versionCode to the backend floor', () => {
    expect(isAndroidVersionBelowMinimum('2', 3)).toBe(true)
    expect(isAndroidVersionBelowMinimum('3', 3)).toBe(false)
    expect(isAndroidVersionBelowMinimum('2', 0)).toBe(false)
    expect(isAndroidVersionBelowMinimum('2', null)).toBe(false)
    expect(isAndroidVersionBelowMinimum('abc', 3)).toBe(false)
    expect(isAndroidVersionBelowMinimum('', 3)).toBe(false)
    expect(isAndroidVersionBelowMinimum(' 2', 3)).toBe(false)
    expect(isAndroidVersionBelowMinimum('2.5', 3)).toBe(false)
  })

  it('snoozes only the same available version for 24 hours', () => {
    const snooze = { availableVersionCode: '3', snoozedUntilMs: 2_000 }
    expect(isSnoozeActive(snooze, '3', 1_999)).toBe(true)
    expect(isSnoozeActive(snooze, '3', 2_000)).toBe(false)
    expect(isSnoozeActive(snooze, '4', 1_999)).toBe(false)
  })

  it('shows a flexible prompt when Play has an installable update', () => {
    expect(
      decideAndroidAppUpdatePrompt({
        play: play(),
        minSupportedVersionCode: 0,
        nowMs: 1_000,
        snooze: null,
      }),
    ).toEqual({ action: 'show_flexible' })
  })

  it('keeps the same version snoozed', () => {
    expect(
      decideAndroidAppUpdatePrompt({
        play: play(),
        minSupportedVersionCode: 0,
        nowMs: 1_000,
        snooze: { availableVersionCode: '3', snoozedUntilMs: 2_000 },
      }),
    ).toEqual({ action: 'none' })
  })

  it('reprompts a newer available version during snooze', () => {
    expect(
      decideAndroidAppUpdatePrompt({
        play: play({ availableVersionCode: '4' }),
        minSupportedVersionCode: 0,
        nowMs: 1_000,
        snooze: { availableVersionCode: '3', snoozedUntilMs: 2_000 },
      }),
    ).toEqual({ action: 'show_flexible' })
  })

  it('forces only when below the floor and Play is installable', () => {
    expect(
      decideAndroidAppUpdatePrompt({
        play: play({ currentVersionCode: '2' }),
        minSupportedVersionCode: 3,
        nowMs: 1_000,
        snooze: { availableVersionCode: '3', snoozedUntilMs: 9_000 },
      }),
    ).toEqual({ action: 'show_force' })
  })

  it('never blocks when below the floor without an installable Play update', () => {
    expect(
      decideAndroidAppUpdatePrompt({
        play: play({
          updateAvailability: 1,
          flexibleUpdateAllowed: false,
          immediateUpdateAllowed: false,
        }),
        minSupportedVersionCode: 4,
        nowMs: 1_000,
        snooze: null,
      }),
    ).toEqual({ action: 'log_force_unavailable' })
    expect(
      decideAndroidAppUpdatePrompt({
        play: play({ flexibleUpdateAllowed: false, immediateUpdateAllowed: false }),
        minSupportedVersionCode: 4,
        nowMs: 1_000,
        snooze: null,
      }),
    ).toEqual({ action: 'log_force_unavailable' })
    expect(
      decideAndroidAppUpdatePrompt({
        play: null,
        minSupportedVersionCode: 4,
        nowMs: 1_000,
        snooze: null,
      }),
    ).toEqual({ action: 'none' })
  })

  it('resumes in-progress and completes downloaded flexible updates', () => {
    expect(
      decideAndroidAppUpdatePrompt({
        play: play({ updateAvailability: PLAY_UPDATE_IN_PROGRESS }),
        minSupportedVersionCode: 0,
        nowMs: 1_000,
        snooze: null,
      }),
    ).toEqual({ action: 'resume_in_progress' })
    expect(
      decideAndroidAppUpdatePrompt({
        play: play({ installStatus: PLAY_INSTALL_DOWNLOADED }),
        minSupportedVersionCode: 0,
        nowMs: 1_000,
        snooze: null,
      }),
    ).toEqual({ action: 'complete_downloaded' })
  })

  it('prefers immediate only when Play allows it', () => {
    expect(resolvePlayUpdateStartType(play(), 'immediate')).toBe('immediate')
    expect(
      resolvePlayUpdateStartType(play({ immediateUpdateAllowed: false }), 'immediate'),
    ).toBe('flexible')
    expect(
      resolvePlayUpdateStartType(
        play({ flexibleUpdateAllowed: false, immediateUpdateAllowed: false }),
        'immediate',
      ),
    ).toBeNull()
  })
})
