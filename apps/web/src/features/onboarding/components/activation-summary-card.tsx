import { AlertTriangle, ArrowRight, CheckCircle2, LoaderCircle, ShieldCheck } from 'lucide-react'
import { useMemo } from 'react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import type { ActivationSummaryResponse } from '@/features/onboarding/types'
import { useActivateOnboardingSession, useMarkReady } from '@/features/onboarding/hooks'
import {
  BlockerList,
  OnboardingErrorState,
  OnboardingLoadingState,
  OnboardingNotice,
  RetryButton,
  getOnboardingErrorBlockers,
  getOnboardingErrorMessage,
} from './onboarding-state'

type ActivationSummaryCardProps = {
  activationSummary: ActivationSummaryResponse | null
  error: unknown
  isLoading: boolean
  onRetry: () => void
  sessionId: string
}

export function ActivationSummaryCard({
  activationSummary,
  error,
  isLoading,
  onRetry,
  sessionId,
}: ActivationSummaryCardProps) {
  const markReadyMutation = useMarkReady(sessionId)
  const activateMutation = useActivateOnboardingSession(sessionId)
  const markReadyBlockers = getOnboardingErrorBlockers(markReadyMutation.error)
  const activationBlockers = getOnboardingErrorBlockers(activateMutation.error)
  const isActivated = Boolean(
    activationSummary?.readiness.session_status === 'activated' &&
      activationSummary.readiness.establishment_status === 'active',
  )

  const canMarkReady = Boolean(
    !isActivated &&
      activationSummary?.effective_can_activate &&
      activationSummary.access.can_activate &&
      activationSummary.readiness.is_ready,
  )
  const canActivate = Boolean(
    !isActivated &&
      activationSummary?.readiness.session_status === 'ready_for_activation' &&
      activationSummary.effective_can_activate &&
      activationSummary.access.can_activate &&
      activationSummary.readiness.is_ready,
  )

  const summaryRows = useMemo(() => {
    if (!activationSummary) {
      return []
    }

    return [
      ['Owner/director memberships', activationSummary.initial_owner_director_count],
      ['Manager memberships', activationSummary.initial_manager_count],
      ['Managers with domains', activationSummary.managers_with_domains_count],
      ['Active modules', activationSummary.active_modules.length],
      ['Active domains', activationSummary.active_domains.length],
      ['Active subjects', activationSummary.active_subjects.length],
    ] as const
  }, [activationSummary])

  async function handleMarkReady() {
    try {
      await markReadyMutation.mutateAsync()
    } catch {
      // The mutation state renders the backend error below.
    }
  }

  async function handleActivate() {
    try {
      await activateMutation.mutateAsync()
    } catch {
      // The mutation state renders the backend error below.
    }
  }

  if (isLoading) {
    return <OnboardingLoadingState label="Loading activation summary..." />
  }

  if (error) {
    return (
      <div className="space-y-3">
        <OnboardingErrorState error={error} fallback="Activation summary could not be loaded." />
        <RetryButton onClick={onRetry} />
      </div>
    )
  }

  if (!activationSummary) {
    return (
      <OnboardingNotice
        tone="muted"
        title="Activation summary is not available yet."
        message="Load an onboarding session before reviewing backend readiness."
      />
    )
  }

  return (
    <Card className="rounded-[1.75rem] border-[#ece5da] bg-[#fffdf9] shadow-[0_22px_48px_-38px_rgba(59,90,184,0.28)]">
      <CardHeader className="gap-3">
        <div className="flex flex-wrap gap-2">
          <Badge className="w-fit bg-[color:var(--primary)]/12 text-[color:var(--primary)]">
            Activation summary
          </Badge>
          <Badge
            variant="outline"
            className={
              activationSummary.readiness.is_ready
                ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
                : 'border-[#ebe2d5] bg-[#fbf7f0]'
            }
          >
            {isActivated ? 'activated' : activationSummary.readiness.is_ready ? 'ready' : 'not ready'}
          </Badge>
        </div>

        <div className="space-y-2">
          <CardTitle className="text-[1.55rem] font-black tracking-[-0.05em]">
            Backend readiness
          </CardTitle>
          <CardDescription className="text-sm leading-6">
            Houston marks this session ready only when the backend readiness response allows it.
          </CardDescription>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        <div className="grid gap-2 sm:grid-cols-2">
          {summaryRows.map(([label, value]) => (
            <div
              key={label}
              className="rounded-[1rem] border border-[#ebe2d5] bg-white px-4 py-3"
            >
              <div className="text-xs text-muted-foreground">{label}</div>
              <div className="mt-1 text-xl font-black tracking-[-0.05em]">{value}</div>
            </div>
          ))}
        </div>

        {isActivated ? (
          <div className="flex items-center gap-2 rounded-[1rem] border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
            <CheckCircle2 className="size-4" />
            Establishment activation was completed by the backend.
          </div>
        ) : activationSummary.blockers.length > 0 ? (
          <BlockerList blockers={activationSummary.blockers} />
        ) : (
          <div className="flex items-center gap-2 rounded-[1rem] border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
            <CheckCircle2 className="size-4" />
            No backend blockers were returned.
          </div>
        )}

        {markReadyMutation.error ? (
          <div className="space-y-3 rounded-[1rem] border border-[#f4d5d5] bg-[#fff3f2] px-4 py-3 text-sm text-[#9d3b33]">
            <div>
              {getOnboardingErrorMessage(
                markReadyMutation.error,
                'Onboarding session could not be marked ready.',
              )}
            </div>
            {markReadyBlockers.length > 0 ? <BlockerList blockers={markReadyBlockers} /> : null}
          </div>
        ) : null}

        {markReadyMutation.isSuccess ? (
          <div className="flex items-center gap-2 rounded-[1rem] border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
            <CheckCircle2 className="size-4" />
            Session readiness was updated by the backend.
          </div>
        ) : null}

        {activateMutation.error ? (
          <div className="space-y-3 rounded-[1rem] border border-[#f4d5d5] bg-[#fff3f2] px-4 py-3 text-sm text-[#9d3b33]">
            <div>
              {getOnboardingErrorMessage(
                activateMutation.error,
                'Onboarding session could not be activated.',
              )}
            </div>
            {activationBlockers.length > 0 ? <BlockerList blockers={activationBlockers} /> : null}
          </div>
        ) : null}

        {activateMutation.isSuccess || isActivated ? (
          <div className="space-y-3 rounded-[1rem] border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="size-4" />
              Activation is complete.
            </div>
            <Button
              asChild
              className="h-11 w-full rounded-[1rem] bg-emerald-700 text-white hover:bg-emerald-800 sm:w-auto"
            >
              <a href="/app">
                Go to workspace
                <ArrowRight className="size-4" />
              </a>
            </Button>
          </div>
        ) : null}

        <div className="rounded-[1.25rem] border border-[#ebe2d5] bg-[#fbf7f0] px-4 py-4">
          <div className="mb-3 flex flex-wrap gap-2">
            <Badge variant="outline" className="border-[#ebe2d5] bg-white">
              session: {activationSummary.readiness.session_status}
            </Badge>
            <Badge variant="outline" className="border-[#ebe2d5] bg-white">
              establishment: {activationSummary.readiness.establishment_status}
            </Badge>
          </div>

          <Button
            type="button"
            className="h-11 w-full rounded-[1rem]"
            disabled={!canMarkReady || markReadyMutation.isPending}
            onClick={handleMarkReady}
          >
            {markReadyMutation.isPending ? (
              <>
                <LoaderCircle className="size-4 animate-spin" />
                Marking ready...
              </>
            ) : (
              <>
                <ShieldCheck className="size-4" />
                Mark ready
              </>
            )}
          </Button>
          <p className="mt-3 text-xs leading-5 text-muted-foreground">
            This does not activate the establishment. It only calls the backend mark-ready
            endpoint when the backend response allows it.
          </p>
        </div>

        {!isActivated ? (
          <div className="rounded-[1.25rem] border border-amber-200 bg-amber-50 px-4 py-4">
            <div className="mb-3 flex items-start gap-2 text-sm text-amber-900">
              <AlertTriangle className="mt-0.5 size-4 shrink-0" />
              <span>
                Activation is explicit and final for this onboarding session. The backend will
                re-check readiness before changing the establishment to active.
              </span>
            </div>

            <Button
              type="button"
              className="h-11 w-full rounded-[1rem]"
              disabled={!canActivate || activateMutation.isPending || activateMutation.isSuccess}
              onClick={handleActivate}
            >
              {activateMutation.isPending ? (
                <>
                  <LoaderCircle className="size-4 animate-spin" />
                  Activating...
                </>
              ) : (
                <>
                  <ShieldCheck className="size-4" />
                  Activate establishment
                </>
              )}
            </Button>
          </div>
        ) : null}
      </CardContent>
    </Card>
  )
}
