/// <reference lib="webworker" />
import { cleanupOutdatedCaches, precacheAndRoute } from 'workbox-precaching'

import {
  buildPushNotificationOptions,
  handleNotificationClick,
  parsePushPayload,
} from './sw/push-handlers'
import { registerSpaNavigationFallback } from './sw/spa-navigation'

declare const self: ServiceWorkerGlobalScope

precacheAndRoute(self.__WB_MANIFEST)
cleanupOutdatedCaches()
registerSpaNavigationFallback()

self.addEventListener('push', (event) => {
  const { title, options } = buildPushNotificationOptions(parsePushPayload(event.data ?? null))
  event.waitUntil(self.registration.showNotification(title, options))
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()

  event.waitUntil(
    handleNotificationClick(
      self.clients,
      event.notification.data as Record<string, unknown> | undefined,
      self.location.origin,
    ),
  )
})
