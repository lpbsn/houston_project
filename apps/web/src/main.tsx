import { QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import App from './App'
import { createBrowserHistory } from '@/app/app-history'
import { AppRouteProvider } from '@/app/app-routes'
import { AuthProvider } from '@/app/auth-provider'
import { ObservationProcessingTrackerProvider } from '@/features/observations/components/observation-processing-tracker-provider'
import { queryClient } from '@/lib/query-client'
import './styles/globals.css'

function unregisterServiceWorkers(): void {
  if (!('serviceWorker' in navigator)) {
    return
  }

  void navigator.serviceWorker.getRegistrations().then((registrations) => {
    for (const registration of registrations) {
      void registration.unregister()
    }
  })
}

unregisterServiceWorkers()

const history = createBrowserHistory()

async function bootstrap() {
  if (import.meta.env.VITE_APP_RUNTIME === 'native') {
    try {
      const { configureNativeBodyRefreshTokenStore } = await import(
        '@/features/auth/native-refresh-token-store'
      )
      await configureNativeBodyRefreshTokenStore()
    } catch {
      // Store stays unconfigured; AuthProvider restore/login remain fail-closed.
    }

    try {
      const { configureNativeAppLifecycle } = await import('@/lib/app-lifecycle')
      await configureNativeAppLifecycle()
    } catch {
      // Web visibility remains the lifecycle source.
    }

    try {
      const { configureNativeNetworkStatus } = await import('@/lib/network-status')
      await configureNativeNetworkStatus()
    } catch {
      // navigator.onLine remains the network source.
    }

    try {
      const { configureNativePush } = await import('@/lib/native-push')
      await configureNativePush({ history })
    } catch {
      // Push stays unconfigured; in-app notifications remain.
    }

    try {
      const { configureNativeDeepLinks } = await import('@/lib/native-deep-link')
      await configureNativeDeepLinks({ history })
    } catch {
      // Deep links stay unconfigured; in-app routing remains.
    }

    try {
      const { configureNativeSystemBack } = await import('@/lib/native-system-back')
      await configureNativeSystemBack({ history })
    } catch {
      // Android system back stays on the WebView default.
    }
  }

  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <ObservationProcessingTrackerProvider>
            <AppRouteProvider history={history}>
              <App />
            </AppRouteProvider>
          </ObservationProcessingTrackerProvider>
        </AuthProvider>
      </QueryClientProvider>
    </StrictMode>,
  )
}

void bootstrap()
