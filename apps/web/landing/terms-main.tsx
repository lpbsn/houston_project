import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import { TermsOfUsePage } from '@/features/landing/pages/terms-of-use-page'
import '@/styles/landing.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <TermsOfUsePage />
  </StrictMode>,
)
