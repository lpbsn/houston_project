/// <reference lib="webworker" />
import { cleanupOutdatedCaches, precacheAndRoute } from 'workbox-precaching'

import {
  buildPushNotificationOptions,
  parsePushPayload,
  resolveNotificationClickUrl,
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

  const url = resolveNotificationClickUrl(
    event.notification.data as Record<string, unknown> | undefined,
    self.location.origin,
  )

  if (!url) {
    return
  }

  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
      for (const client of clientList) {
        if (client.url === url && 'focus' in client) {
          return client.focus()
        }
      }

      if (self.clients.openWindow) {
        return self.clients.openWindow(url)
      }

      return undefined
    }),
  )
})
