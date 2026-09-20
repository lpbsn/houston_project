import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { resolveInvitationErrorMessage } from '@/features/auth/lib/invitation-errors'
import { DraftOnboardingWizard } from '@/features/onboarding/components/draft-onboarding-wizard'
import {
  completePlatformOnboarding,
  getPlatformOnboarding,
  getPlatformOnboardingDraft,
  invitePlatformOwner,
  platformQueryKeys,
  putPlatformOnboardingDraft,
} from '@/features/platform/api'
import { PlatformLink } from '@/features/platform/components/platform-link'
import { PlatformFunctionalStatusBadge } from '@/features/platform/components/platform-status-badge'
import { usePlatformListSearch, withSearchQuery } from '@/features/platform/lib/platform-search'

type PlatformOnboardingWizardPageProps = {
  sessionId: string
  onNavigate: (path: string) => void
}

export function PlatformOnboardingWizardPage({
  sessionId,
  onNavigate,
}: PlatformOnboardingWizardPageProps) {
  const queryClient = useQueryClient()
  const { q } = usePlatformListSearch('/platform/onboardings')
  const listHref = withSearchQuery('/platform/onboardings', q)
  const summaryQuery = useQuery({
    queryKey: platformQueryKeys.onboarding(sessionId),
    queryFn: () => getPlatformOnboarding(sessionId),
  })
  const [email, setEmail] = useState('')
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [inviteError, setInviteError] = useState<string | null>(null)
  const inviteMutation = useMutation({
    mutationFn: () =>
      invitePlatformOwner(sessionId, {
        email: email.trim(),
        first_name: firstName.trim(),
        last_name: lastName.trim(),
      }),
    onSuccess: async () => {
      setInviteError(null)
      setEmail('')
      setFirstName('')
      setLastName('')
      await queryClient.invalidateQueries({ queryKey: platformQueryKeys.onboarding(sessionId) })
    },
    onError: (error) => {
      setInviteError(resolveInvitationErrorMessage(error, 'Impossible d’inviter l’Owner.'))
    },
  })

  const summary = summaryQuery.data
  const functionalStatus = summary?.functional_status ?? null
  const showWizard = functionalStatus !== 'activated'

  if (summaryQuery.isPending) {
    return <p className="text-sm text-[var(--platform-muted)]">Chargement…</p>
  }
  if (summaryQuery.isError) {
    return (
      <div data-testid="platform-error" className="space-y-3">
        <p className="text-sm text-[var(--platform-status-problem-fg)]">Onboarding introuvable.</p>
        <PlatformLink href={listHref} className="text-sm hover:underline">
          Retour aux onboardings
        </PlatformLink>
      </div>
    )
  }

  return (
    <div>
      <nav className="mb-4 text-sm text-[var(--platform-muted)]">
        <PlatformLink href={listHref} className="hover:underline">
          Onboardings
        </PlatformLink>
        <span aria-hidden> / </span>
        <span className="text-[var(--platform-text)]">
          {summary?.organization_name ?? 'Onboarding'}
        </span>
      </nav>
      <div className="mb-6 flex flex-wrap items-center gap-3">
        <h2 className="text-2xl font-semibold">{summary?.organization_name ?? 'Onboarding'}</h2>
        <PlatformFunctionalStatusBadge status={functionalStatus} />
      </div>
      <p className="mb-6 text-sm text-[var(--platform-muted)]">
        {summary?.establishment_name ?? '—'}
      </p>

      {showWizard ? (
        <form
          className="mb-8 grid max-w-[800px] gap-3 rounded-xl border border-[var(--platform-border)] bg-[var(--platform-surface)] p-4"
          onSubmit={(event) => {
            event.preventDefault()
            inviteMutation.mutate()
          }}
        >
          <p className="text-sm font-medium">Invitation Owner</p>
          <Input
            required
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="E-mail"
          />
          <div className="grid grid-cols-2 gap-3">
            <Input
              required
              value={firstName}
              onChange={(event) => setFirstName(event.target.value)}
              placeholder="Prénom"
            />
            <Input
              required
              value={lastName}
              onChange={(event) => setLastName(event.target.value)}
              placeholder="Nom"
            />
          </div>
          {inviteError ? (
            <p className="text-sm text-[var(--platform-status-problem-fg)]">{inviteError}</p>
          ) : null}
          <Button type="submit" className="h-10 w-fit" disabled={inviteMutation.isPending}>
            Inviter l’Owner
          </Button>
        </form>
      ) : null}

      {showWizard ? (
        <DraftOnboardingWizard
          sessionId={sessionId}
          onNavigate={onNavigate}
          getDraft={getPlatformOnboardingDraft}
          putDraft={putPlatformOnboardingDraft}
          completeSession={completePlatformOnboarding}
          draftQueryKey={platformQueryKeys.draft(sessionId)}
          detailQueryKey={platformQueryKeys.onboarding(sessionId)}
          listQueryKey={['platform', 'onboardings']}
          afterCompletePath={listHref}
        />
      ) : (
        <p className="rounded-xl border border-[var(--platform-border)] bg-[var(--platform-surface)] p-4 text-sm text-[var(--platform-muted)]">
          Cet établissement est activé. Le wizard n’est plus disponible.
        </p>
      )}
    </div>
  )
}
