import { fetchVapidPublicKey, upsertWebPushSubscription } from '../api'

function arrayBufferToBase64Url(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer)
  let binary = ''
  for (let i = 0; i < bytes.length; i += 1) {
    binary += String.fromCharCode(bytes[i])
  }

  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

function urlBase64ToUint8Array(base64String: string): BufferSource {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const rawData = atob(base64)
  const outputArray = new Uint8Array(rawData.length)

  for (let i = 0; i < rawData.length; i += 1) {
    outputArray[i] = rawData.charCodeAt(i)
  }

  return outputArray
}

export async function requestNotificationPermission(): Promise<NotificationPermission> {
  if (!('Notification' in window)) {
    return 'denied'
  }

  if (Notification.permission === 'granted' || Notification.permission === 'denied') {
    return Notification.permission
  }

  return Notification.requestPermission()
}

export async function subscribeToWebPush(): Promise<PushSubscription> {
  if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
    throw new Error('Les notifications push ne sont pas disponibles sur cet appareil.')
  }

  const permission = await requestNotificationPermission()
  if (permission !== 'granted') {
    throw new Error('Autorisation de notification refusée.')
  }

  const { public_key: publicKey } = await fetchVapidPublicKey()
  const registration = await navigator.serviceWorker.ready

  const existingSubscription = await registration.pushManager.getSubscription()
  if (existingSubscription) {
    return existingSubscription
  }

  return registration.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(publicKey),
  })
}

export async function registerWebPushSubscription(): Promise<PushSubscription> {
  const subscription = await subscribeToWebPush()
  const p256dhKey = subscription.getKey('p256dh')
  const authKey = subscription.getKey('auth')

  if (!p256dhKey || !authKey) {
    throw new Error('Impossible de lire la subscription push.')
  }

  await upsertWebPushSubscription({
    endpoint: subscription.endpoint,
    p256dh: arrayBufferToBase64Url(p256dhKey),
    auth: arrayBufferToBase64Url(authKey),
    user_agent: navigator.userAgent,
  })

  return subscription
}
