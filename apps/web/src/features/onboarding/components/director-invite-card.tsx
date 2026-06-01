import { CheckCircle2, Copy, LoaderCircle, UserPlus } from 'lucide-react'
import { useMemo, useState } from 'react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import type { ActivationSummaryResponse } from '@/features/onboarding/types'
import { useInviteDirector } from '@/features/onboarding/hooks'
import {
  BlockerList,
  OnboardingErrorState,
  OnboardingLoadingState,
  OnboardingNotice,
  RetryButton,
  getOnboardingErrorMessage,
} from './onboarding-state'

type DirectorInviteCardProps = {
  activationSummary: ActivationSummaryResponse | null
  error: unknown
  isLoading: boolean
  onRetry: () => void
  sessionId: string
}

type DirectorInviteForm = {
  email: string
  first_name: string
  last_name: string
}

const emptyForm: DirectorInviteForm = {
  email: '',
  first_name: '',
  last_name: '',
}

function hasDirectorReadinessBlocker(activationSummary: ActivationSummaryResponse | null) {
  if (!activationSummary) {
    return true
  }

  return activationSummary.readiness.blockers.some(
    (blocker) => blocker.code === 'missing_active_or_invited_director',
  )
}

function buildInvitationAcceptUrl(acceptPath: string) {
  if (acceptPath.startsWith('http://') || acceptPath.startsWith('https://')) {
    return acceptPath
  }

  return `${window.location.origin}${acceptPath.startsWith('/') ? acceptPath : `/${acceptPath}`}`
}

export function DirectorInviteCard({
  activationSummary,
  error,
  isLoading,
  onRetry,
  sessionId,
}: DirectorInviteCardProps) {
  const [form, setForm] = useState<DirectorInviteForm>(emptyForm)
  const [invitationLink, setInvitationLink] = useState<string | null>(null)
  const [copyMessage, setCopyMessage] = useState<string | null>(null)
  const inviteMutation = useInviteDirector(sessionId)

  const directorCount = activationSummary?.initial_director_count ?? 0
  const hasDirector = directorCount > 0
  const needsDirector = hasDirectorReadinessBlocker(activationSummary)
  const isActivated = Boolean(
    activationSummary?.readiness.session_status === 'activated' &&
      activationSummary.readiness.establishment_status === 'active',
  )

  const canSubmit = useMemo(() => {
    return (
      !isActivated &&
      !hasDirector &&
      form.email.trim().length > 0 &&
      form.first_name.trim().length > 0 &&
      form.last_name.trim().length > 0
    )
  }, [form.email, form.first_name, form.last_name, hasDirector, isActivated])

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setCopyMessage(null)

    try {
      const response = await inviteMutation.mutateAsync({
        email: form.email.trim(),
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim(),
      })
      setInvitationLink(buildInvitationAcceptUrl(response.invitation_accept_path))
      setForm(emptyForm)
    } catch {
      setInvitationLink(null)
    }
  }

  async function handleCopyLink() {
    if (!invitationLink) {
      return
    }

    try {
      await navigator.clipboard.writeText(invitationLink)
      setCopyMessage('Invitation link copied.')
    } catch {
      setCopyMessage('Copy failed. Select the link and copy it manually.')
    }
  }

  if (isLoading) {
    return <OnboardingLoadingState label="Loading director invitation status..." />
  }

  if (error) {
    return (
      <div className="space-y-3">
        <OnboardingErrorState
          error={error}
          fallback="Director invitation status could not be loaded."
        />
        <RetryButton onClick={onRetry} />
      </div>
    )
  }

  if (!activationSummary) {
    return (
      <OnboardingNotice
        tone="muted"
        title="Director invitation is not available yet."
        message="Load activation readiness before inviting a Director."
      />
    )
  }

  return (
    <Card className="rounded-[1.75rem] border-[#ece5da] bg-[#fffdf9] shadow-[0_22px_48px_-38px_rgba(59,90,184,0.28)]">
      <CardHeader className="gap-3">
        <div className="flex flex-wrap gap-2">
          <Badge className="w-fit bg-[color:var(--primary)]/12 text-[color:var(--primary)]">
            Director
          </Badge>
          {hasDirector ? (
            <Badge variant="outline" className="border-emerald-200 bg-emerald-50 text-emerald-700">
              Director invited or active
            </Badge>
          ) : (
            <Badge variant="outline" className="border-amber-200 bg-amber-50 text-amber-800">
              required before activation
            </Badge>
          )}
        </div>

        <div className="space-y-2">
          <CardTitle className="text-[1.55rem] font-black tracking-[-0.05em]">
            Invite a Director
          </CardTitle>
          <CardDescription className="text-sm leading-6">
            Each establishment has exactly one Director (invited or active), distinct from the
            Owner. Share the invitation link with them after sending the invite.
          </CardDescription>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {isActivated ? (
          <OnboardingNotice
            tone="muted"
            title="Establishment activated."
            message="Director invitations are no longer required for this onboarding session."
          />
        ) : hasDirector ? (
          <OnboardingNotice
            tone="muted"
            title="Director already invited."
            message="This establishment already has an invited or active Director. Share the link you received when the invite was sent."
          />
        ) : (
          <form className="space-y-4" onSubmit={handleSubmit}>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-2 sm:col-span-2">
                <label className="text-sm font-semibold" htmlFor="director-email">
                  Email
                </label>
                <Input
                  id="director-email"
                  type="email"
                  autoComplete="email"
                  value={form.email}
                  onChange={(event) => {
                    setForm((current) => ({ ...current, email: event.target.value }))
                    setCopyMessage(null)
                  }}
                  className="h-11 rounded-[1rem] border-[#e7dfd1] bg-[#fffaf2]"
                  placeholder="director@example.com"
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-semibold" htmlFor="director-first-name">
                  First name
                </label>
                <Input
                  id="director-first-name"
                  value={form.first_name}
                  onChange={(event) => {
                    setForm((current) => ({ ...current, first_name: event.target.value }))
                    setCopyMessage(null)
                  }}
                  className="h-11 rounded-[1rem] border-[#e7dfd1] bg-[#fffaf2]"
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-semibold" htmlFor="director-last-name">
                  Last name
                </label>
                <Input
                  id="director-last-name"
                  value={form.last_name}
                  onChange={(event) => {
                    setForm((current) => ({ ...current, last_name: event.target.value }))
                    setCopyMessage(null)
                  }}
                  className="h-11 rounded-[1rem] border-[#e7dfd1] bg-[#fffaf2]"
                />
              </div>
            </div>

            {needsDirector ? (
              <BlockerList
                blockers={[
                  {
                    code: 'missing_active_or_invited_director',
                    message: 'Invite a Director before mark-ready and activation.',
                  },
                ]}
              />
            ) : null}

            {inviteMutation.error ? (
              <p className="text-sm text-destructive">
                {getOnboardingErrorMessage(
                  inviteMutation.error,
                  'Director invitation could not be sent.',
                )}
              </p>
            ) : null}

            <Button
              type="submit"
              disabled={!canSubmit || inviteMutation.isPending}
              className="h-11 w-full rounded-[1rem] sm:w-auto"
            >
              {inviteMutation.isPending ? (
                <>
                  <LoaderCircle className="size-4 animate-spin" />
                  Sending invitation...
                </>
              ) : (
                <>
                  <UserPlus className="size-4" />
                  Invite Director
                </>
              )}
            </Button>
          </form>
        )}

        {invitationLink ? (
          <div className="space-y-3 rounded-[1rem] border border-emerald-200 bg-emerald-50/60 p-4">
            <div className="flex items-center gap-2 text-sm font-semibold text-emerald-800">
              <CheckCircle2 className="size-4" />
              Director invitation link
            </div>
            <p className="break-all text-sm text-emerald-900">{invitationLink}</p>
            <Button
              type="button"
              variant="outline"
              className="h-10 rounded-[1rem] border-emerald-200 bg-white"
              onClick={() => {
                void handleCopyLink()
              }}
            >
              <Copy className="size-4" />
              Copy invitation link
            </Button>
            {copyMessage ? <p className="text-sm text-emerald-800">{copyMessage}</p> : null}
          </div>
        ) : null}
      </CardContent>
    </Card>
  )
}
