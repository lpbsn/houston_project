import { createHandlerBoundToURL } from 'workbox-precaching'
import { NavigationRoute, registerRoute } from 'workbox-routing'

import { SPA_NAVIGATION_DENYLIST } from './spa-navigation-policy'

export { shouldBypassSpaNavigation } from './spa-navigation-policy'

export function registerSpaNavigationFallback(): void {
  registerRoute(
    new NavigationRoute(createHandlerBoundToURL('/index.html'), {
      denylist: SPA_NAVIGATION_DENYLIST,
    }),
  )
}
