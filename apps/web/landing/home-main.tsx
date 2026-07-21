import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import { LandingPage } from '@/features/landing/pages/landing-page'
import '@/styles/landing.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <LandingPage />
  </StrictMode>,
)
