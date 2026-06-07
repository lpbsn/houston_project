import { ArrowRight, Building2 } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  buildOnboardingUrl,
  type PendingOnboardingMembership,
} from '@/features/auth/lib/pending-onboarding'

type PendingOnboardingSelectionCardProps = {
  pendingMemberships: PendingOnboardingMembership[]
  onContinueOnboarding: (path: string) => void
  onShowWaiting: () => void
}

export function PendingOnboardingSelectionCard({
  pendingMemberships,
  onContinueOnboarding,
  onShowWaiting,
}: PendingOnboardingSelectionCardProps) {
  return (
    <Card className="mx-auto w-full max-w-2xl rounded-[1.85rem] border-[#ece5da] bg-[#fffdf9] shadow-[0_24px_52px_-40px_rgba(46,72,173,0.28)]">
      <CardHeader className="gap-3">
        <CardTitle className="text-[1.55rem] font-black tracking-[-0.05em]">
          Choisissez un établissement
        </CardTitle>
        <CardDescription className="text-sm leading-6">
          Plusieurs établissements sont encore en cours de configuration. Sélectionnez celui
          que vous souhaitez reprendre.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {pendingMemberships.map((pending) => (
          <div
            key={pending.id}
            className="flex flex-col gap-3 rounded-[1.25rem] border border-[#ece5da] bg-white px-4 py-4 sm:flex-row sm:items-center sm:justify-between"
          >
            <div className="flex items-start gap-3">
              <span className="rounded-full bg-[color:var(--primary)]/10 p-2 text-[color:var(--primary)]">
                <Building2 className="size-4" />
              </span>
              <div className="space-y-1">
                <p className="font-semibold">{pending.establishment_name}</p>
                <p className="text-sm text-muted-foreground">
                  Rôle : {pending.role} · Statut : {pending.establishment_status}
                </p>
              </div>
            </div>
            <Button
              type="button"
              className="h-10 rounded-[1rem]"
              onClick={() => {
                if (pending.can_continue_onboarding) {
                  onContinueOnboarding(buildOnboardingUrl(pending))
                  return
                }

                onShowWaiting()
              }}
            >
              {pending.can_continue_onboarding ? 'Continuer la configuration' : 'Voir le statut'}
              <ArrowRight className="size-4" />
            </Button>
          </div>
        ))}
      </CardContent>
    </Card>
  )
}
