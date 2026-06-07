import { MembershipInviteCard } from '@/features/auth/components/membership-invite-card'
import { DirectorInviteCard } from '@/features/onboarding/components/director-invite-card'
import type { ActivationSummaryResponse } from '@/features/onboarding/types'

type ManualOnboardingV2InvitationsStepProps = {
  activationSummary: ActivationSummaryResponse | null
  activationSummaryError: unknown
  establishmentId: string
  isActivationSummaryLoading: boolean
  onRetryActivationSummary: () => void
  sessionId: string
}

export function ManualOnboardingV2InvitationsStep({
  activationSummary,
  activationSummaryError,
  establishmentId,
  isActivationSummaryLoading,
  onRetryActivationSummary,
  sessionId,
}: ManualOnboardingV2InvitationsStepProps) {
  return (
    <div className="space-y-5">
      <div>
        <h3 className="text-lg font-semibold">Étape 4 — Invitations</h3>
        <p className="text-sm leading-6 text-muted-foreground">
          Invitez un directeur puis les membres de l&apos;équipe avec leurs périmètres de pôles.
        </p>
      </div>

      <DirectorInviteCard
        activationSummary={activationSummary}
        error={activationSummaryError}
        isLoading={isActivationSummaryLoading}
        onRetry={onRetryActivationSummary}
        sessionId={sessionId}
      />

      <MembershipInviteCard establishmentId={establishmentId} allowedTargetRoles={['manager', 'staff']} />
    </div>
  )
}
