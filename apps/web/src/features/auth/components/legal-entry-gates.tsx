import type { PropsWithChildren } from 'react'

import { useAuth } from '@/app/auth-provider'
import { LegalConsentSheet } from '@/features/auth/components/legal-consent-sheet'
import { readAiConsentStatus } from '@/lib/legal'

export function LegalEntryGates({ children }: PropsWithChildren) {
  const { bootstrap, isAuthenticated } = useAuth()
  const user = bootstrap?.user
  const needsTerms = Boolean(user?.needs_terms_acceptance)
  const aiStatus = readAiConsentStatus(user)
  const kind = !isAuthenticated || !user ? null : needsTerms ? 'terms' : aiStatus === 'undecided' ? 'ai' : null

  return (
    <>
      {children}
      <LegalConsentSheet
        kind={kind}
        allowDismiss={false}
        onClose={() => undefined}
        onAccepted={() => undefined}
      />
    </>
  )
}
