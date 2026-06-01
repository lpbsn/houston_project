import { ArrowLeft } from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import { useAuth } from '@/app/auth-provider'
import { Button } from '@/components/ui/button'
import { ActivityDescriptionCard } from '@/features/onboarding/components/activity-description-card'
import { ActivationSummaryCard } from '@/features/onboarding/components/activation-summary-card'
import { DirectorInviteCard } from '@/features/onboarding/components/director-invite-card'
import { OnboardingHeroCard } from '@/features/onboarding/components/onboarding-hero-card'
import { OnboardingRegistrationCard } from '@/features/onboarding/components/onboarding-registration-card'
import { OnboardingStartCard } from '@/features/onboarding/components/onboarding-start-card'
import {
  OnboardingErrorState,
  OnboardingLoadingState,
  OnboardingNotice,
} from '@/features/onboarding/components/onboarding-state'
import { ProposalCard } from '@/features/onboarding/components/proposal-card'
import { RuntimeConfigCard } from '@/features/onboarding/components/runtime-config-card'
import {
  useActivationSummary,
  useOnboardingSession,
  useRuntimeConfig,
  useStartOnboardingSession,
} from '@/features/onboarding/hooks'

type OnboardingRouteParams = {
  establishmentId: string | null
  sessionId: string | null
}

function readRouteParams(): OnboardingRouteParams {
  const params = new URLSearchParams(window.location.search)

  return {
    establishmentId: params.get('establishmentId'),
    sessionId: params.get('sessionId'),
  }
}

function writeRouteParams(nextParams: OnboardingRouteParams) {
  const searchParams = new URLSearchParams()

  if (nextParams.establishmentId) {
    searchParams.set('establishmentId', nextParams.establishmentId)
  }

  if (nextParams.sessionId) {
    searchParams.set('sessionId', nextParams.sessionId)
  }

  const query = searchParams.toString()
  const nextUrl = query ? `/onboarding?${query}` : '/onboarding'

  window.history.replaceState(null, '', nextUrl)
}

export function OnboardingPage() {
  const { isAuthenticated, isReady } = useAuth()
  const [routeParams, setRouteParams] = useState<OnboardingRouteParams>(() => readRouteParams())
  const startMutation = useStartOnboardingSession()
  const autoStartAttemptedRef = useRef(false)

  useEffect(() => {
    const handlePopState = () => {
      setRouteParams(readRouteParams())
    }

    window.addEventListener('popstate', handlePopState)

    return () => {
      window.removeEventListener('popstate', handlePopState)
    }
  }, [])

  const handleRegistered = useCallback((result: { establishmentId: string; sessionId: string }) => {
    const nextParams = {
      establishmentId: result.establishmentId,
      sessionId: result.sessionId,
    }

    writeRouteParams(nextParams)
    setRouteParams(nextParams)
  }, [])

  const sessionQuery = useOnboardingSession(routeParams.sessionId, {
    enabled: Boolean(routeParams.sessionId) && isAuthenticated,
  })
  const runtimeConfigQuery = useRuntimeConfig(routeParams.sessionId, {
    enabled: Boolean(routeParams.sessionId) && isAuthenticated,
  })
  const activationSummaryQuery = useActivationSummary(routeParams.sessionId, {
    enabled: Boolean(routeParams.sessionId) && isAuthenticated,
  })

  const activityDescription = useMemo(
    () =>
      runtimeConfigQuery.data?.activity_description ??
      activationSummaryQuery.data?.activity_description ??
      null,
    [activationSummaryQuery.data?.activity_description, runtimeConfigQuery.data?.activity_description],
  )

  const canGenerateProposal = Boolean(activityDescription?.validated_at)

  const handleStartSession = useCallback(async () => {
    if (!routeParams.establishmentId) {
      return
    }

    try {
      const response = await startMutation.mutateAsync({
        establishment_id: routeParams.establishmentId,
        source_mode: 'manual',
      })
      const nextParams = {
        establishmentId: routeParams.establishmentId,
        sessionId: response.session.id,
      }

      writeRouteParams(nextParams)
      setRouteParams(nextParams)
    } catch {
      // The start card renders the backend error from mutation state.
    }
  }, [routeParams.establishmentId, startMutation])

  useEffect(() => {
    autoStartAttemptedRef.current = false
  }, [routeParams.establishmentId])

  useEffect(() => {
    if (
      !isAuthenticated ||
      routeParams.sessionId ||
      !routeParams.establishmentId ||
      autoStartAttemptedRef.current
    ) {
      return
    }

    autoStartAttemptedRef.current = true
    void handleStartSession()
  }, [handleStartSession, isAuthenticated, routeParams.establishmentId, routeParams.sessionId])

  if (!isReady) {
    return <OnboardingLoadingState label="Checking your session..." />
  }

  if (!routeParams.sessionId && !routeParams.establishmentId) {
    if (!isAuthenticated) {
      return <OnboardingRegistrationCard onRegistered={handleRegistered} />
    }

    return (
      <OnboardingNotice
        tone="muted"
        title="Open onboarding from your workspace."
        message="Choose an establishment from your workspace to start or resume onboarding."
        actions={
          <Button
            asChild
            variant="outline"
            className="h-11 w-full rounded-[1rem] border-[#e7dfd1] bg-[#fffaf2] sm:w-auto"
          >
            <a href="/app">
              <ArrowLeft className="size-4" />
              Back to workspace
            </a>
          </Button>
        }
      />
    )
  }

  if (!routeParams.sessionId && routeParams.establishmentId) {
    if (startMutation.isPending || startMutation.isSuccess) {
      return <OnboardingLoadingState label="Starting onboarding session..." />
    }

    return (
      <OnboardingStartCard
        establishmentId={routeParams.establishmentId}
        error={startMutation.error}
        isStarting={startMutation.isPending}
        onStart={handleStartSession}
      />
    )
  }

  if (sessionQuery.isPending) {
    return <OnboardingLoadingState label="Loading onboarding session..." />
  }

  if (sessionQuery.error) {
    return (
      <OnboardingErrorState
        error={sessionQuery.error}
        fallback="Onboarding session could not be loaded."
      />
    )
  }

  if (!sessionQuery.data || !routeParams.sessionId) {
    return (
      <OnboardingNotice
        tone="muted"
        title="No onboarding session loaded."
        message="The onboarding route did not return a session from the backend."
      />
    )
  }

  return (
    <div className="space-y-4 sm:space-y-5">
      <OnboardingHeroCard
        activationSummary={activationSummaryQuery.data ?? null}
        runtimeConfig={runtimeConfigQuery.data ?? null}
        session={sessionQuery.data}
      />

      <ActivityDescriptionCard
        activityDescription={activityDescription}
        sessionId={routeParams.sessionId}
      />

      <ProposalCard canGenerateProposal={canGenerateProposal} sessionId={routeParams.sessionId} />

      <RuntimeConfigCard
        error={runtimeConfigQuery.error}
        isLoading={runtimeConfigQuery.isPending}
        onRetry={() => {
          void runtimeConfigQuery.refetch()
        }}
        runtimeConfig={runtimeConfigQuery.data ?? null}
      />

      <DirectorInviteCard
        activationSummary={activationSummaryQuery.data ?? null}
        error={activationSummaryQuery.error}
        isLoading={activationSummaryQuery.isPending}
        onRetry={() => {
          void activationSummaryQuery.refetch()
        }}
        sessionId={routeParams.sessionId}
      />

      <ActivationSummaryCard
        activationSummary={activationSummaryQuery.data ?? null}
        error={activationSummaryQuery.error}
        isLoading={activationSummaryQuery.isPending}
        onRetry={() => {
          void activationSummaryQuery.refetch()
        }}
        sessionId={routeParams.sessionId}
      />
    </div>
  )
}
