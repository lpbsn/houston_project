import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import { PrivacyPolicyPage } from '@/features/landing/pages/privacy-policy-page'
import '@/styles/landing.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <PrivacyPolicyPage />
  </StrictMode>,
)
