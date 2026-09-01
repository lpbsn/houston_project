import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import { AccountDeletionPage } from '@/features/landing/pages/account-deletion-page'
import '@/styles/landing.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AccountDeletionPage />
  </StrictMode>,
)
