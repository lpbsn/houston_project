import type { AppHistory } from '@/app/app-history'
import { switchEstablishment } from '@/features/auth/api'
import { getAccessToken } from '@/features/auth/session'
import { markNotificationRead } from '@/features/notifications/api'
import { revokePushDevice, upsertPushDevice } from '@/features/notifications/push-devices-api'
import { getAppRuntime } from '@/lib/runtime'

import {
  NativePushPermissionDeniedError,
  readNativePushActiveEstablishmentId,
  registerNativePushController,
} from './native-push-session'
import { applyNativePushTap, parseNativePushTapPayload, type NativePushTapTarget } from './native-push-tap'

type PermissionReceive = 'granted' | 'denied' | 'prompt'

let nativeConfigured = false
let currentToken: string | null = null
let currentDeviceId: string | null = null
let bufferedToken: string | null = null
let pendingTap: NativePushTapTarget | null = null
let applyingTap = false
let history: AppHistory | null = null
const removeListeners: Array<() => Promise<void>> = []

async function loadNativeDeps() {
  const { Capacitor } = await import('@capacitor/core')
  const { FirebaseMessaging } = await import('@capacitor-firebase/messaging')
  return { Capacitor, FirebaseMessaging }
}

function extractNotificationData(event: unknown): unknown {
  if (!event || typeof event !== 'object') {
    return null
  }
  const notification = 'notification' in event ? event.notification : null
  if (!notification || typeof notification !== 'object') {
    return null
  }
  if ('data' in notification) {
    return notification.data
  }
  return notification
}

async function upsertToken(token: string) {
  if (!token || !getAccessToken()) {
    bufferedToken = token
    return
  }

  const { Capacitor } = await loadNativeDeps()
  const platform = Capacitor.getPlatform()
  if (platform !== 'ios' && platform !== 'android') {
    return
  }

  if (token === currentToken && currentDeviceId) {
    bufferedToken = null
    return
  }

  const previousDeviceId = currentDeviceId
  const previousToken = currentToken
  const device = await upsertPushDevice({ token, platform })
  currentToken = token
  currentDeviceId = device.id
  bufferedToken = null

  if (previousDeviceId && previousToken && previousToken !== token) {
    try {
      await revokePushDevice(previousDeviceId)
    } catch {
      // Stale token is revoked on FCM UNREGISTERED.
    }
  }
}

async function handleTokenReceived(token: string) {
  if (!getAccessToken()) {
    bufferedToken = token
    return
  }
  await upsertToken(token)
}

async function handleTapEvent(event: unknown) {
  const target = parseNativePushTapPayload(extractNotificationData(event))
  if (!target) {
    return
  }
  pendingTap = target
  await applyPendingTap()
}

async function applyPendingTap() {
  if (!pendingTap || !history || applyingTap || !getAccessToken()) {
    return
  }

  applyingTap = true
  const target = pendingTap
  try {
    await applyNativePushTap(target, {
      getActiveEstablishmentId: readNativePushActiveEstablishmentId,
      switchEstablishment: async (establishmentId) => {
        await switchEstablishment({ establishment_id: establishmentId })
      },
      navigate: (url) => {
        history?.navigate(url)
      },
      markNotificationRead: async (establishmentId, notificationId) => {
        await markNotificationRead(establishmentId, notificationId)
      },
    })
    pendingTap = null
  } catch {
    // Keep pending tap; a later session-ready retry can apply it.
  } finally {
    applyingTap = false
  }
}

async function checkReceivePermission(): Promise<PermissionReceive | 'unavailable'> {
  if (!nativeConfigured) {
    return 'unavailable'
  }
  const { FirebaseMessaging } = await loadNativeDeps()
  const permissions = await FirebaseMessaging.checkPermissions()
  if (
    permissions.receive === 'granted' ||
    permissions.receive === 'denied' ||
    permissions.receive === 'prompt'
  ) {
    return permissions.receive
  }
  if (permissions.receive === 'prompt-with-rationale') {
    return 'prompt'
  }
  return 'denied'
}

async function syncTokenIfGranted() {
  if (!nativeConfigured || !getAccessToken()) {
    if (bufferedToken && getAccessToken()) {
      await upsertToken(bufferedToken)
    }
    return
  }

  const receive = await checkReceivePermission()
  if (receive !== 'granted') {
    return
  }

  const { FirebaseMessaging } = await loadNativeDeps()
  const { token } = await FirebaseMessaging.getToken()
  if (token) {
    await upsertToken(token)
  }
}

async function optIn() {
  if (!nativeConfigured) {
    throw new Error('Native push is not available.')
  }

  const { FirebaseMessaging } = await loadNativeDeps()
  const permissions = await FirebaseMessaging.requestPermissions()
  if (permissions.receive !== 'granted') {
    throw new NativePushPermissionDeniedError()
  }

  const { token } = await FirebaseMessaging.getToken()
  if (!token) {
    throw new Error('Push token was not issued.')
  }
  await upsertToken(token)
}

async function beforeLogout() {
  const deviceId = currentDeviceId
  currentToken = null
  currentDeviceId = null
  bufferedToken = null
  pendingTap = null

  if (deviceId && getAccessToken()) {
    try {
      await revokePushDevice(deviceId)
    } catch {
      // Next account upsert reassigns the token.
    }
  }

  if (!nativeConfigured) {
    return
  }
  try {
    const { FirebaseMessaging } = await loadNativeDeps()
    await FirebaseMessaging.deleteToken()
  } catch {
    // Local delete is best-effort after revoke.
  }
}

export async function configureNativePush(options: { history: AppHistory }) {
  if (getAppRuntime() !== 'native') {
    return
  }

  const { Capacitor, FirebaseMessaging } = await loadNativeDeps()
  if (!Capacitor.isNativePlatform()) {
    return
  }

  history = options.history

  let tokenHandle: { remove: () => Promise<void> } | null = null
  let tapHandle: { remove: () => Promise<void> } | null = null
  try {
    tokenHandle = await FirebaseMessaging.addListener('tokenReceived', (event) => {
      void handleTokenReceived(event.token)
    })
    tapHandle = await FirebaseMessaging.addListener('notificationActionPerformed', (event) => {
      void handleTapEvent(event)
    })
    removeListeners.push(() => tokenHandle!.remove(), () => tapHandle!.remove())
    nativeConfigured = true
    registerNativePushController({
      optIn,
      checkReceivePermission,
      syncTokenIfGranted,
      applyPendingTap,
      beforeLogout,
    })
  } catch (error) {
    if (tokenHandle) {
      await tokenHandle.remove()
    }
    if (tapHandle) {
      await tapHandle.remove()
    }
    nativeConfigured = false
    history = null
    registerNativePushController(null)
    throw error
  }
}

export async function resetNativePushForTests() {
  for (const remove of removeListeners.splice(0)) {
    await remove()
  }
  nativeConfigured = false
  currentToken = null
  currentDeviceId = null
  bufferedToken = null
  pendingTap = null
  applyingTap = false
  history = null
  registerNativePushController(null)
}
