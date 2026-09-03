import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import { SupportPage } from '@/features/landing/pages/support-page'
import '@/styles/landing.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <SupportPage />
  </StrictMode>,
)
