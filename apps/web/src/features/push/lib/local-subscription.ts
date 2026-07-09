export async function getLocalPushSubscription(): Promise<PushSubscription | null> {
  if (!('serviceWorker' in navigator)) {
    return null
  }

  const registration = await navigator.serviceWorker.ready
  return registration.pushManager.getSubscription()
}
