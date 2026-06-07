import { ArrowLeft } from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import { useAuth } from '@/app/auth-provider'
import { Button } from '@/components/ui/button'
import { resolvePendingLanding } from '@/features/auth/lib/pending-onboarding'
import { ActivationSummaryCard } from '@/features/onboarding/components/activation-summary-card'
import { ManualOnboardingV2Wizard } from '@/features/onboarding/components/manual-onboarding-v2-wizard'
import { OnboardingHeroCard } from '@/features/onboarding/components/onboarding-hero-card'
import { OnboardingRegistrationCard } from '@/features/onboarding/components/onboarding-registration-card'
import { OnboardingStartCard } from '@/features/onboarding/components/onboarding-start-card'
import {
  OnboardingErrorState,
  OnboardingLoadingState,
  OnboardingNotice,
} from '@/features/onboarding/components/onboarding-state'
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

export function OnboardingPage({ onNavigate }: { onNavigate?: (path: string) => void }) {
  const {
    activeMembership,
    hasOperationalAccess,
    isAuthenticated,
    isReady,
    pendingOnboardingMemberships,
  } = useAuth()
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

  const effectiveRouteParams = useMemo(() => {
    if (routeParams.establishmentId || routeParams.sessionId) {
      return routeParams
    }

    if (!isReady || !isAuthenticated) {
      return routeParams
    }

    const landing = resolvePendingLanding(pendingOnboardingMemberships)
    if (landing.kind !== 'onboarding') {
      return routeParams
    }

    return {
      establishmentId: landing.pending.establishment_id,
      sessionId: landing.pending.onboarding_session_id,
    }
  }, [
    isAuthenticated,
    isReady,
    pendingOnboardingMemberships,
    routeParams,
  ])

  useEffect(() => {
    if (
      routeParams.establishmentId ||
      routeParams.sessionId ||
      !effectiveRouteParams.establishmentId
    ) {
      return
    }

    writeRouteParams(effectiveRouteParams)
  }, [effectiveRouteParams, routeParams.establishmentId, routeParams.sessionId])

  useEffect(() => {
    if (
      !isReady ||
      !isAuthenticated ||
      !hasOperationalAccess ||
      !onNavigate ||
      !effectiveRouteParams.establishmentId
    ) {
      return
    }

    if (activeMembership?.establishment_id === effectiveRouteParams.establishmentId) {
      onNavigate('/app/operational-config')
    }
  }, [
    activeMembership?.establishment_id,
    effectiveRouteParams.establishmentId,
    hasOperationalAccess,
    isAuthenticated,
    isReady,
    onNavigate,
  ])

  const sessionQuery = useOnboardingSession(effectiveRouteParams.sessionId, {
    enabled: Boolean(effectiveRouteParams.sessionId) && isAuthenticated,
  })
  const runtimeConfigQuery = useRuntimeConfig(effectiveRouteParams.sessionId, {
    enabled: Boolean(effectiveRouteParams.sessionId) && isAuthenticated,
  })
  const activationSummaryQuery = useActivationSummary(effectiveRouteParams.sessionId, {
    enabled: Boolean(effectiveRouteParams.sessionId) && isAuthenticated,
  })

  const handleStartSession = useCallback(async () => {
    if (!effectiveRouteParams.establishmentId) {
      return
    }

    try {
      const response = await startMutation.mutateAsync({
        establishment_id: effectiveRouteParams.establishmentId,
        source_mode: 'manual',
      })
      const nextParams = {
        establishmentId: effectiveRouteParams.establishmentId,
        sessionId: response.session.id,
      }

      writeRouteParams(nextParams)
      setRouteParams(nextParams)
    } catch {
      // The start card renders the backend error from mutation state.
    }
  }, [effectiveRouteParams.establishmentId, startMutation])

  useEffect(() => {
    autoStartAttemptedRef.current = false
  }, [effectiveRouteParams.establishmentId])

  useEffect(() => {
    if (
      !isAuthenticated ||
      effectiveRouteParams.sessionId ||
      !effectiveRouteParams.establishmentId ||
      autoStartAttemptedRef.current
    ) {
      return
    }

    autoStartAttemptedRef.current = true
    void handleStartSession()
  }, [
    effectiveRouteParams.establishmentId,
    effectiveRouteParams.sessionId,
    handleStartSession,
    isAuthenticated,
  ])

  if (
    hasOperationalAccess &&
    effectiveRouteParams.establishmentId &&
    activeMembership?.establishment_id === effectiveRouteParams.establishmentId
  ) {
    return <OnboardingLoadingState label="Redirection vers la configuration opérationnelle…" />
  }

  if (!isReady) {
    return <OnboardingLoadingState label="Vérification de votre session…" />
  }

  if (!effectiveRouteParams.sessionId && !effectiveRouteParams.establishmentId) {
    if (!isAuthenticated) {
      return <OnboardingRegistrationCard onRegistered={handleRegistered} />
    }

    const landing = resolvePendingLanding(pendingOnboardingMemberships)

    if (landing.kind === 'waiting' || landing.kind === 'selection') {
      return (
        <OnboardingNotice
          tone="muted"
          title="Configuration en cours"
          message="Votre établissement est encore en cours de configuration. Retournez à l’écran d’attente pour suivre l’avancement."
          actions={
            <Button
              type="button"
              variant="outline"
              className="h-11 w-full rounded-[1rem] border-[#e7dfd1] bg-[#fffaf2] sm:w-auto"
              onClick={() => onNavigate?.('/pending-onboarding')}
            >
              <ArrowLeft className="size-4" />
              Voir le statut
            </Button>
          }
        />
      )
    }

    return (
      <OnboardingNotice
        tone="muted"
        title="Ouvrez l’onboarding depuis votre espace."
        message="Choisissez un établissement en cours de configuration pour démarrer ou reprendre l’onboarding."
        actions={
          <Button
            type="button"
            variant="outline"
            className="h-11 w-full rounded-[1rem] border-[#e7dfd1] bg-[#fffaf2] sm:w-auto"
            onClick={() => onNavigate?.('/pending-onboarding')}
          >
            <ArrowLeft className="size-4" />
            Voir les établissements en attente
          </Button>
        }
      />
    )
  }

  if (!effectiveRouteParams.sessionId && effectiveRouteParams.establishmentId) {
    if (startMutation.isPending || startMutation.isSuccess) {
      return <OnboardingLoadingState label="Démarrage de la session d’onboarding…" />
    }

    return (
      <OnboardingStartCard
        establishmentId={effectiveRouteParams.establishmentId}
        error={startMutation.error}
        isStarting={startMutation.isPending}
        onStart={handleStartSession}
      />
    )
  }

  if (sessionQuery.isPending) {
    return <OnboardingLoadingState label="Chargement de la session d’onboarding…" />
  }

  if (sessionQuery.error) {
    return (
      <OnboardingErrorState
        error={sessionQuery.error}
        fallback="La session d’onboarding n’a pas pu être chargée."
      />
    )
  }

  if (!sessionQuery.data || !effectiveRouteParams.sessionId) {
    return (
      <OnboardingNotice
        tone="muted"
        title="Aucune session d’onboarding chargée."
        message="La route d’onboarding n’a pas renvoyé de session depuis le backend."
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

      <ManualOnboardingV2Wizard
        activationSummary={activationSummaryQuery.data ?? null}
        activationSummaryError={activationSummaryQuery.error}
        establishmentId={sessionQuery.data.establishment.id}
        isActivationSummaryLoading={activationSummaryQuery.isPending}
        onApplied={() => {
          void runtimeConfigQuery.refetch()
          void activationSummaryQuery.refetch()
        }}
        onRetryActivationSummary={() => {
          void activationSummaryQuery.refetch()
        }}
        runtimeConfig={runtimeConfigQuery.data ?? null}
        sessionId={effectiveRouteParams.sessionId}
      />

      <ActivationSummaryCard
        activationSummary={activationSummaryQuery.data ?? null}
        error={activationSummaryQuery.error}
        isLoading={activationSummaryQuery.isPending}
        onNavigate={onNavigate}
        onRetry={() => {
          void activationSummaryQuery.refetch()
        }}
        sessionId={effectiveRouteParams.sessionId}
      />
    </div>
  )
}
