import { QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import App from './App'
import { createBrowserHistory } from '@/app/app-history'
import { AppRouteProvider } from '@/app/app-routes'
import { AuthProvider } from '@/app/auth-provider'
import { ObservationProcessingTrackerProvider } from '@/features/observations/components/observation-processing-tracker-provider'
import { notifyPwaUpdateAvailable } from '@/lib/pwa-update'
import { queryClient } from '@/lib/query-client'
import './styles/globals.css'

if (import.meta.env.PROD) {
  void import('virtual:pwa-register').then(({ registerSW }) => {
    const updateSW = registerSW({
      immediate: false,
      onNeedRefresh() {
        notifyPwaUpdateAvailable(() => updateSW())
      },
    })
  })
}

const history = createBrowserHistory()

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
