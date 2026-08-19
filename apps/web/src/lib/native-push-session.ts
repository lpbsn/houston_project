export class NativePushPermissionDeniedError extends Error {
  constructor() {
    super('Notification permission was not granted.')
    this.name = 'NativePushPermissionDeniedError'
  }
}

type NativePushController = {
  optIn: () => Promise<void>
  checkReceivePermission: () => Promise<'granted' | 'denied' | 'prompt' | 'unavailable'>
  syncTokenIfGranted: () => Promise<void>
  applyPendingTap: () => Promise<void>
  beforeLogout: () => Promise<void>
}

let controller: NativePushController | null = null

export function registerNativePushController(next: NativePushController | null) {
  controller = next
}

export function isNativePushConfigured(): boolean {
  return controller !== null
}

export async function optInNativePush() {
  if (!controller) {
    throw new Error('Native push is not available.')
  }
  await controller.optIn()
}

export async function checkNativePushReceivePermission() {
  if (!controller) {
    return 'unavailable' as const
  }
  return controller.checkReceivePermission()
}

export async function syncNativePushTokenIfGranted() {
  if (!controller) {
    return
  }
  await controller.syncTokenIfGranted()
}

export async function applyPendingNativePushTap() {
  if (!controller) {
    return
  }
  await controller.applyPendingTap()
}

export async function runNativePushBeforeLogout() {
  if (!controller) {
    return
  }
  try {
    await controller.beforeLogout()
  } catch {
    // Best-effort: logout must still proceed.
  }
}

let getActiveEstablishmentId: () => string | null = () => null

export function setNativePushActiveEstablishmentGetter(getter: () => string | null) {
  getActiveEstablishmentId = getter
}

export function readNativePushActiveEstablishmentId() {
  return getActiveEstablishmentId()
}
