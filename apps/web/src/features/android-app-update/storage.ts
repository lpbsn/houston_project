import { ANDROID_APP_UPDATE_STORAGE_KEY, SNOOZE_DURATION_MS } from './constants'
import type { AndroidAppUpdateSnooze } from './rules'

export type AndroidAppUpdateStoredState = {
  lastCheckAtMs: number | null
  snooze: AndroidAppUpdateSnooze | null
}

function getLocalStorage(): Storage | null {
  if (typeof window === 'undefined') {
    return null
  }
  try {
    return window.localStorage ?? null
  } catch {
    return null
  }
}

function isSnooze(value: unknown): value is AndroidAppUpdateSnooze {
  if (!value || typeof value !== 'object') {
    return false
  }
  const snooze = value as AndroidAppUpdateSnooze
  return (
    typeof snooze.availableVersionCode === 'string' &&
    snooze.availableVersionCode.length > 0 &&
    typeof snooze.snoozedUntilMs === 'number' &&
    Number.isFinite(snooze.snoozedUntilMs)
  )
}

export function readAndroidAppUpdateState(): AndroidAppUpdateStoredState {
  const storage = getLocalStorage()
  if (!storage) {
    return { lastCheckAtMs: null, snooze: null }
  }

  try {
    const raw = storage.getItem(ANDROID_APP_UPDATE_STORAGE_KEY)
    if (!raw) {
      return { lastCheckAtMs: null, snooze: null }
    }
    const parsed = JSON.parse(raw) as Partial<AndroidAppUpdateStoredState>
    return {
      lastCheckAtMs:
        typeof parsed.lastCheckAtMs === 'number' && Number.isFinite(parsed.lastCheckAtMs)
          ? parsed.lastCheckAtMs
          : null,
      snooze: isSnooze(parsed.snooze) ? parsed.snooze : null,
    }
  } catch {
    return { lastCheckAtMs: null, snooze: null }
  }
}

function writeAndroidAppUpdateState(next: AndroidAppUpdateStoredState): void {
  const storage = getLocalStorage()
  if (!storage) {
    return
  }
  try {
    storage.setItem(ANDROID_APP_UPDATE_STORAGE_KEY, JSON.stringify(next))
  } catch {
    // Best-effort device preference.
  }
}

export function markAndroidAppUpdateChecked(nowMs: number): AndroidAppUpdateStoredState {
  const current = readAndroidAppUpdateState()
  const next = { ...current, lastCheckAtMs: nowMs }
  writeAndroidAppUpdateState(next)
  return next
}

export function snoozeAndroidAppUpdate(
  availableVersionCode: string,
  nowMs: number,
): AndroidAppUpdateStoredState {
  const current = readAndroidAppUpdateState()
  const next = {
    ...current,
    snooze: {
      availableVersionCode,
      snoozedUntilMs: nowMs + SNOOZE_DURATION_MS,
    },
  }
  writeAndroidAppUpdateState(next)
  return next
}

export function clearAndroidAppUpdateStateForTests(): void {
  getLocalStorage()?.removeItem(ANDROID_APP_UPDATE_STORAGE_KEY)
}
