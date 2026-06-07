import { useMemo, useState } from 'react'

import { EstablishmentPendingActivationCard } from '@/features/auth/components/establishment-pending-activation-card'
import { PendingOnboardingSelectionCard } from '@/features/auth/components/pending-onboarding-selection-card'
import { resolvePendingLanding } from '@/features/auth/lib/pending-onboarding'
import type { PendingOnboardingMembership } from '@/features/auth/lib/pending-onboarding'
import type { Membership } from '@/features/auth/types'

type PendingOnboardingPageProps = {
  pendingMemberships: PendingOnboardingMembership[]
  memberships: Membership[]
  onNavigate: (path: string) => void
}

export function PendingOnboardingPage({
  pendingMemberships,
  memberships,
  onNavigate,
}: PendingOnboardingPageProps) {
  const [forceWaiting, setForceWaiting] = useState(false)
  const landing = useMemo(
    () => resolvePendingLanding(pendingMemberships),
    [pendingMemberships],
  )

  if (pendingMemberships.length === 0 && memberships.length === 0) {
    return (
      <div className="rounded-[1.25rem] border border-[#ece5da] bg-[#fffdf9] px-4 py-8 text-sm text-muted-foreground">
        Aucun établissement en attente n&apos;est disponible pour ce compte.
      </div>
    )
  }

  if (pendingMemberships.length === 0) {
    return (
      <div className="rounded-[1.25rem] border border-[#ece5da] bg-[#fffdf9] px-4 py-8 text-sm text-muted-foreground">
        Aucun établissement en cours de configuration. Utilisez la sélection d&apos;établissement
        pour accéder à votre espace opérationnel.
      </div>
    )
  }

  if (forceWaiting || landing.kind === 'waiting') {
    return <EstablishmentPendingActivationCard />
  }

  if (landing.kind === 'selection') {
    return (
      <PendingOnboardingSelectionCard
        pendingMemberships={landing.pendingMemberships}
        onContinueOnboarding={onNavigate}
        onShowWaiting={() => setForceWaiting(true)}
      />
    )
  }

  return <EstablishmentPendingActivationCard />
}
