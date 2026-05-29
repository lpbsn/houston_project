import { ArrowLeft } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'

import { Button } from '@/components/ui/button'
import { ActivityDescriptionCard } from '@/features/onboarding/components/activity-description-card'
import { ActivationSummaryCard } from '@/features/onboarding/components/activation-summary-card'
import { OnboardingHeroCard } from '@/features/onboarding/components/onboarding-hero-card'
import { OnboardingStartCard } from '@/features/onboarding/components/onboarding-start-card'
import {
  OnboardingErrorState,
  OnboardingLoadingState,
  OnboardingNotice,
} from '@/features/onboarding/components/onboarding-state'
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

export function OnboardingPage() {
  const [routeParams, setRouteParams] = useState<OnboardingRouteParams>(() => readRouteParams())
  const startMutation = useStartOnboardingSession()

  useEffect(() => {
    const handlePopState = () => {
      setRouteParams(readRouteParams())
    }

    window.addEventListener('popstate', handlePopState)

    return () => {
      window.removeEventListener('popstate', handlePopState)
    }
  }, [])

  const sessionQuery = useOnboardingSession(routeParams.sessionId, {
    enabled: Boolean(routeParams.sessionId),
  })
  const runtimeConfigQuery = useRuntimeConfig(routeParams.sessionId, {
    enabled: Boolean(routeParams.sessionId),
  })
  const activationSummaryQuery = useActivationSummary(routeParams.sessionId, {
    enabled: Boolean(routeParams.sessionId),
  })

  const activityDescription = useMemo(
    () =>
      runtimeConfigQuery.data?.activity_description ??
      activationSummaryQuery.data?.activity_description ??
      null,
    [activationSummaryQuery.data?.activity_description, runtimeConfigQuery.data?.activity_description],
  )

  async function handleStartSession() {
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
      const searchParams = new URLSearchParams({
        establishmentId: nextParams.establishmentId,
        sessionId: nextParams.sessionId,
      })

      window.history.replaceState(null, '', `/onboarding?${searchParams.toString()}`)
      setRouteParams(nextParams)
    } catch {
      // The start card renders the backend error from mutation state.
    }
  }

  if (!routeParams.sessionId && !routeParams.establishmentId) {
    return (
      <OnboardingNotice
        tone="muted"
        title="Open onboarding from a workspace."
        message="This page needs an establishment id to start onboarding or a session id to load an existing onboarding session."
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

      <RuntimeConfigCard
        error={runtimeConfigQuery.error}
        isLoading={runtimeConfigQuery.isPending}
        onRetry={() => {
          void runtimeConfigQuery.refetch()
        }}
        runtimeConfig={runtimeConfigQuery.data ?? null}
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
