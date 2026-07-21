import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import { LegalPage } from '@/features/landing/pages/legal-page'
import '@/styles/landing.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <LegalPage />
  </StrictMode>,
)
