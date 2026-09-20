import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { DraftOnboardingWizard } from '@/features/onboarding/components/draft-onboarding-wizard'
import { getCompleteErrorMessage } from '@/features/onboarding/lib/onboarding-draft-errors'
import {
  completePlatformOnboarding,
  getPlatformOnboarding,
  getPlatformOnboardingDraft,
  invitePlatformOwner,
  platformQueryKeys,
  putPlatformOnboardingDraft,
} from '@/features/platform/api'
import { formatFunctionalStatus } from '@/features/platform/lib/functional-status'

type PlatformOnboardingWizardPageProps = {
  sessionId: string
  onNavigate: (path: string) => void
}

export function PlatformOnboardingWizardPage({
  sessionId,
  onNavigate,
}: PlatformOnboardingWizardPageProps) {
  const queryClient = useQueryClient()
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
      setInviteError(getCompleteErrorMessage(error, 'Impossible d’inviter l’Owner.'))
    },
  })

  const summary = summaryQuery.data
  const functionalStatus = summary?.functional_status ?? null
  const showWizard = functionalStatus !== 'activated'

  return (
    <div>
      <button
        type="button"
        className="mb-4 text-sm text-slate-600 hover:underline"
        onClick={() => onNavigate('/platform/onboardings')}
      >
        ← Onboardings
      </button>
      <div className="mb-6">
        <h2 className="text-2xl font-semibold">{summary?.organization_name ?? 'Onboarding'}</h2>
        <p className="mt-1 text-sm text-slate-600">
          {summary?.establishment_name ?? '—'} · {formatFunctionalStatus(functionalStatus)}
        </p>
      </div>

      {showWizard ? (
        <form
          className="mb-8 grid max-w-xl gap-3 rounded-xl border border-slate-200 bg-white p-4"
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
          {inviteError ? <p className="text-sm text-red-600">{inviteError}</p> : null}
          <Button type="submit" disabled={inviteMutation.isPending}>
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
          afterCompletePath="/platform/onboardings"
        />
      ) : (
        <p className="rounded-xl border border-slate-200 bg-white p-4 text-sm text-slate-600">
          Cet établissement est activé. Le wizard n’est plus disponible.
        </p>
      )}
    </div>
  )
}
