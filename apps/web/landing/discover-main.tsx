import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import { DiscoveryPage } from '@/features/landing/pages/discovery-page'
import '@/styles/landing.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <DiscoveryPage />
  </StrictMode>,
)
