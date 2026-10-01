import { LoaderCircle } from 'lucide-react'
import { useEffect, useLayoutEffect, useRef, useState } from 'react'

import { useAppRoute } from '@/app/app-routes'
import { useAuth } from '@/app/auth-provider'
import { TerrainFeedback } from '@/components/domain/terrain-feedback'
import { TerrainErrorState, TerrainStickyFooter, TerrainSwitch } from '@/components/ui/terrain'
import { Button } from '@/components/ui/button'
import { isDesktopWebLanding } from '@/features/auth/lib/authenticated-landing'
import { notifySuccess } from '@/lib/success-toast'
import { useNativeKeyboardOpen } from '@/lib/native-keyboard'
import { useLgViewport } from '@/lib/lg-viewport'
import { terrainBrandAction } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

import {
  ActionPlanLaunchPlanning,
  type ActionPlanLaunchTiming,
} from '../components/action-plan-launch-planning'
import { useActionPlanDetailQuery, useSubmitActionPlanPlanningMutation } from '../hooks'
import { resolvePlanningSuccessPath } from '../lib/action-plan-create-response'
import {
  formatPlanningSubmitFeedback,
  isCatalogPlanningPrimaryDisabled,
  resolveCatalogPlanningSubmit,
  resolveCatalogPlanningSubmitFallbackMessage,
  submitCatalogPlanningWithIntent,
  validateCatalogPlanningDraft,
} from '../lib/action-plan-catalog-planning-submit'
import { resolveActionPlanErrorMessage } from '../lib/action-plan-errors'
import { guideToFirstActionPlanFieldError } from '../lib/action-plan-form-guidance'
import {
  createActionPlanEventPlanningDraft,
  type ActionPlanEventPlanningDraft,
} from '../lib/action-plan-event-planning-form'
import { isStaffActionPlanUsageRole } from '../lib/action-plan-management-access'
import {
  canShowActionPlanSchedule,
  canShowActionPlanUse,
} from '../lib/action-plan-permission-hints'

type ActionPlanTemplateUsePageProps = {
  actionPlanId: string
}

function draftForLaunch(
  draft: ActionPlanEventPlanningDraft,
  timing: ActionPlanLaunchTiming,
): ActionPlanEventPlanningDraft {
  if (timing === 'now' && !draft.usePerAssigneeChronology) {
    return {
      ...createActionPlanEventPlanningDraft(),
      assignees: draft.assignees,
    }
  }
  return draft
}

function formatTaskCount(count: number): string {
  return count === 1 ? '1 tâche' : `${count} tâches`
}

export function ActionPlanTemplateUsePage({ actionPlanId }: ActionPlanTemplateUsePageProps) {
  const { navigate } = useAppRoute()
  const { activeMembership, bootstrap } = useAuth()
  const isDesktopWeb = isDesktopWebLanding(useLgViewport())
  const isNativeKeyboardOpen = useNativeKeyboardOpen()
  const establishmentId = activeMembership?.establishment_id ?? null
  const staffUseMode = isStaffActionPlanUsageRole(activeMembership?.role ?? null)
  const staffDisplayName = bootstrap?.user?.username ?? 'Moi'

  const detailQuery = useActionPlanDetailQuery(
    isDesktopWeb ? null : establishmentId,
    actionPlanId,
  )
  const planningMutation = useSubmitActionPlanPlanningMutation(establishmentId ?? '')

  const [timing, setTiming] = useState<ActionPlanLaunchTiming>('now')
  const [requiresValidationChoice, setRequiresValidationChoice] = useState<boolean | null>(null)
  const [advancedOpen, setAdvancedOpen] = useState(false)
  const [draft, setDraft] = useState<ActionPlanEventPlanningDraft>(createActionPlanEventPlanningDraft)
  const [hasAttemptedSubmit, setHasAttemptedSubmit] = useState(false)
  const [guidanceNonce, setGuidanceNonce] = useState(0)
  const [feedback, setFeedback] = useState<string | null>(null)
  const formRootRef = useRef<HTMLDivElement>(null)
  const lastGuidanceNonceRef = useRef(0)

  useLayoutEffect(() => {
    if (!isDesktopWeb) {
      return
    }
    navigate(`/action-plans/${actionPlanId}`, { replace: true })
  }, [actionPlanId, isDesktopWeb, navigate])

  const plan = detailQuery.data
  const canSchedule = plan ? canShowActionPlanSchedule(plan.permission_hints) : false
  const planningOptions = { canSchedule, staffMode: staffUseMode }
  const launchDraft = draftForLaunch(draft, timing)
  const fieldErrors = hasAttemptedSubmit
    ? validateCatalogPlanningDraft(launchDraft, {
        canSchedule,
        staffMode: staffUseMode,
      })
    : {}

  useEffect(() => {
    if (guidanceNonce <= lastGuidanceNonceRef.current) {
      return
    }
    lastGuidanceNonceRef.current = guidanceNonce
    if (Object.keys(fieldErrors).length === 0) {
      return
    }
    return guideToFirstActionPlanFieldError(fieldErrors, {
      root: formRootRef.current ?? document,
    })
  }, [fieldErrors, guidanceNonce])

  if (isDesktopWeb) {
    return null
  }

  if (!establishmentId) {
    return null
  }

  if (detailQuery.isLoading) {
    return (
      <div className="flex items-center justify-center gap-2 px-3 py-10 text-sm text-[#7D7B75]">
        <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden />
        Chargement du plan...
      </div>
    )
  }

  if (detailQuery.isError || !plan) {
    return (
      <TerrainErrorState
        className="mx-3 mt-3"
        message={resolveActionPlanErrorMessage(
          detailQuery.error,
          'Ce plan est introuvable ou inaccessible.',
        )}
        onRetry={() => void detailQuery.refetch()}
      />
    )
  }

  const canUse = canShowActionPlanUse(plan.permission_hints)
  const requiresValidation = requiresValidationChoice ?? plan.requires_validation
  const primaryDisabled = isCatalogPlanningPrimaryDisabled(launchDraft, {
    ...planningOptions,
    isPending: planningMutation.isPending,
  })

  function selectTiming(next: ActionPlanLaunchTiming) {
    setTiming(next)
    if (next === 'now') {
      setDraft((previous) => ({
        ...createActionPlanEventPlanningDraft(),
        assignees: previous.assignees,
      }))
      setAdvancedOpen(false)
    }
  }

  async function handleLaunch() {
    setHasAttemptedSubmit(true)
    const submitted = draftForLaunch(draft, timing)
    const errors = validateCatalogPlanningDraft(submitted, planningOptions)
    if (Object.keys(errors).length > 0) {
      if (Object.keys(errors).some((key) => key === 'assignees' || key.startsWith('assignee.'))) {
        setAdvancedOpen(true)
      }
      setGuidanceNonce((value) => value + 1)
      return
    }

    const submit = resolveCatalogPlanningSubmit(submitted, {
      ...planningOptions,
      requiresValidation,
    })
    if (!submit) {
      return
    }

    setFeedback(null)
    try {
      const response = await submitCatalogPlanningWithIntent({
        establishmentId,
        actionPlanId,
        body: submit.body,
        submit: (body) => planningMutation.mutateAsync({ actionPlanId, body }),
      })
      notifySuccess({
        message: formatPlanningSubmitFeedback(response.summary),
        kind: 'created',
      })
      navigate(resolvePlanningSuccessPath(response))
    } catch (error) {
      setFeedback(
        resolveActionPlanErrorMessage(
          error,
          resolveCatalogPlanningSubmitFallbackMessage(submit, error),
        ),
      )
    }
  }

  return (
    <div data-testid="action-plan-template-use-frame" className="flex min-h-full flex-col">
      <div className={cn('flex flex-col gap-4 px-3 pt-2', canUse ? 'pb-28' : 'pb-4')}>
        {feedback ? <TerrainFeedback variant="error" message={feedback} /> : null}
        <div className="space-y-1">
          <h1 className="text-[17px] font-semibold leading-snug text-[#1a1a1a]">{plan.title}</h1>
          <p className="text-sm text-[#7D7B75]">
            {formatTaskCount(plan.task_count)}
            <span aria-hidden> · </span>
            {plan.pilot_business_unit.specific_name}
          </p>
        </div>

        <div ref={formRootRef}>
          <ActionPlanLaunchPlanning
            draft={draft}
            config={{
              canEditAssignees: !staffUseMode,
              canSchedule,
              staffMode: staffUseMode,
              showAdvancedChronology: !staffUseMode,
              hideAssignees: false,
              staffDisplayName,
              assigneeActionsEnabled: false,
            }}
            establishmentId={establishmentId}
            pilotBusinessUnitId={plan.pilot_business_unit.id}
            fieldErrors={fieldErrors}
            timing={timing}
            advancedOpen={advancedOpen}
            onTimingChange={selectTiming}
            onAdvancedOpenChange={setAdvancedOpen}
            onDraftChange={(update) => {
              setDraft((previous) => (typeof update === 'function' ? update(previous) : update))
            }}
          />
        </div>

        <div className="overflow-hidden rounded-xl border border-[#E8E6DF] bg-white">
          <TerrainSwitch
            label="Validation requise"
            checked={requiresValidation}
            onCheckedChange={setRequiresValidationChoice}
          />
        </div>
      </div>

      {canUse && !isNativeKeyboardOpen ? (
        <TerrainStickyFooter>
          <Button
            type="button"
            className={cn(
              'h-11 w-full rounded-full text-white',
              terrainBrandAction.bg,
              terrainBrandAction.hover,
            )}
            disabled={primaryDisabled || !canUse}
            onClick={() => void handleLaunch()}
          >
            Lancer le plan
          </Button>
        </TerrainStickyFooter>
      ) : null}
    </div>
  )
}
