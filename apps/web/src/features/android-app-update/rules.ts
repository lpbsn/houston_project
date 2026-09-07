import {
  FOREGROUND_CHECK_INTERVAL_MS,
  PLAY_INSTALL_DOWNLOADED,
  PLAY_UPDATE_AVAILABLE,
  PLAY_UPDATE_IN_PROGRESS,
} from './constants'

export type AndroidPlayUpdateSnapshot = {
  currentVersionCode: string
  availableVersionCode: string
  updateAvailability: number
  flexibleUpdateAllowed: boolean
  immediateUpdateAllowed: boolean
  installStatus: number | null
}

export type AndroidAppUpdateSnooze = {
  availableVersionCode: string
  snoozedUntilMs: number
}

export type AndroidAppUpdatePromptDecision =
  | { action: 'none' }
  | { action: 'complete_downloaded' }
  | { action: 'resume_in_progress' }
  | { action: 'show_force' }
  | { action: 'show_flexible' }
  | { action: 'log_force_unavailable' }

export function canUseAndroidInAppUpdates(input: {
  runtime: 'web' | 'native'
  isNativePlatform: boolean
  platform: string
}): boolean {
  return input.runtime === 'native' && input.isNativePlatform && input.platform === 'android'
}

export function shouldCheckPlayOnForeground(lastCheckAtMs: number | null, nowMs: number): boolean {
  if (lastCheckAtMs == null) {
    return true
  }
  return nowMs - lastCheckAtMs >= FOREGROUND_CHECK_INTERVAL_MS
}

export function isPlayUpdateInstallable(play: AndroidPlayUpdateSnapshot): boolean {
  return (
    play.updateAvailability === PLAY_UPDATE_AVAILABLE &&
    (play.flexibleUpdateAllowed || play.immediateUpdateAllowed)
  )
}

export function isAndroidVersionBelowMinimum(
  currentVersionCode: string,
  minSupportedVersionCode: number | null,
): boolean {
  if (minSupportedVersionCode == null || minSupportedVersionCode <= 0) {
    return false
  }
  if (!/^\d+$/.test(currentVersionCode)) {
    return false
  }
  const current = Number(currentVersionCode)
  return Number.isFinite(current) && current < minSupportedVersionCode
}

export function isSnoozeActive(
  snooze: AndroidAppUpdateSnooze | null,
  availableVersionCode: string,
  nowMs: number,
): boolean {
  if (!snooze) {
    return false
  }
  return snooze.availableVersionCode === availableVersionCode && nowMs < snooze.snoozedUntilMs
}

export function decideAndroidAppUpdatePrompt(input: {
  play: AndroidPlayUpdateSnapshot | null
  minSupportedVersionCode: number | null
  nowMs: number
  snooze: AndroidAppUpdateSnooze | null
}): AndroidAppUpdatePromptDecision {
  const { play, minSupportedVersionCode, nowMs, snooze } = input
  if (!play) {
    return { action: 'none' }
  }

  if (play.installStatus === PLAY_INSTALL_DOWNLOADED) {
    return { action: 'complete_downloaded' }
  }

  if (play.updateAvailability === PLAY_UPDATE_IN_PROGRESS) {
    return { action: 'resume_in_progress' }
  }

  const belowMinimum = isAndroidVersionBelowMinimum(play.currentVersionCode, minSupportedVersionCode)
  if (!isPlayUpdateInstallable(play)) {
    return belowMinimum ? { action: 'log_force_unavailable' } : { action: 'none' }
  }

  if (belowMinimum) {
    return { action: 'show_force' }
  }

  if (isSnoozeActive(snooze, play.availableVersionCode, nowMs)) {
    return { action: 'none' }
  }

  return { action: 'show_flexible' }
}

export function resolvePlayUpdateStartType(
  play: AndroidPlayUpdateSnapshot,
  preferred: 'immediate' | 'flexible',
): 'immediate' | 'flexible' | null {
  if (preferred === 'immediate' && play.immediateUpdateAllowed) {
    return 'immediate'
  }
  if (play.flexibleUpdateAllowed) {
    return 'flexible'
  }
  if (play.immediateUpdateAllowed) {
    return 'immediate'
  }
  return null
}
