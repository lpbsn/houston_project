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
      <div className="flex h-full min-h-0 flex-col" inert={kind ? true : undefined}>
        {children}
      </div>
      <LegalConsentSheet
        kind={kind}
        allowDismiss={false}
        onClose={() => undefined}
        onAccepted={() => undefined}
      />
    </>
  )
}
