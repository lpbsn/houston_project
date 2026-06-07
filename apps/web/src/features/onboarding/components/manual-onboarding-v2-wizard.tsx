import { ArrowLeft, ArrowRight, CheckCircle2, LoaderCircle } from 'lucide-react'
import { useEffect, useRef, useState, startTransition } from 'react'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { suggestActivitySubjects } from '@/features/onboarding/api'
import { ManualOnboardingV2BuConfigStep } from '@/features/onboarding/components/manual-onboarding-v2-bu-config-step'
import { ManualOnboardingV2BuPickerStep } from '@/features/onboarding/components/manual-onboarding-v2-bu-picker-step'
import { ManualOnboardingV2InvitationsStep } from '@/features/onboarding/components/manual-onboarding-v2-invitations-step'
import {
  useApplyOnboardingProposal,
  useCreateManualOnboardingProposal,
  useOnboardingProposals,
  useSubmitManualOnboardingProposal,
  useUpdateManualOnboardingProposal,
} from '@/features/onboarding/hooks'
import {
  allBusinessUnitsConfigured,
  buildManualV2Payload,
  createEmptySubjectSeedTrackers,
  deriveWizardStepFromState,
  hydrateDraftFromProposalPayload,
  mergeCatalogSubjectSuggestions,
  pickResumeProposal,
  recordExcludedCatalogSubject,
  removeBusinessUnitFromDraft,
  updateBusinessUnitDescription,
  type DraftActivitySubject,
  type DraftBusinessUnit,
  type SubjectSeedTrackers,
  type WizardResumeStep,
} from '@/features/onboarding/lib/manual-v2-proposal'
import type { ActivationSummaryResponse, RuntimeConfigResponse } from '@/features/onboarding/types'
import {
  BlockerList,
  getOnboardingErrorMessage,
  getOnboardingErrorBlockers,
} from '@/features/onboarding/components/onboarding-state'

type WizardStep = WizardResumeStep

type ManualOnboardingV2WizardProps = {
  activationSummary: ActivationSummaryResponse | null
  activationSummaryError: unknown
  establishmentId: string
  isActivationSummaryLoading: boolean
  onApplied: () => void
  onRetryActivationSummary: () => void
  runtimeConfig: RuntimeConfigResponse | null
  sessionId: string
}

const stepOrder: WizardStep[] = ['poles', 'config', 'apply', 'invitations']

const stepLabels: Record<WizardStep, string> = {
  poles: 'Pôles',
  config: 'Sujets',
  apply: 'Validation',
  invitations: 'Invitations',
}

export function ManualOnboardingV2Wizard({
  activationSummary,
  activationSummaryError,
  establishmentId,
  isActivationSummaryLoading,
  onApplied,
  onRetryActivationSummary,
  runtimeConfig,
  sessionId,
}: ManualOnboardingV2WizardProps) {
  const runtimeAlreadyApplied = (runtimeConfig?.active_business_units?.length ?? 0) > 0
  const proposalsQuery = useOnboardingProposals(sessionId)
  const [hydrated, setHydrated] = useState(false)
  const [step, setStep] = useState<WizardStep>('poles')
  const [maxReachedStepIndex, setMaxReachedStepIndex] = useState(0)
  const [businessUnits, setBusinessUnits] = useState<DraftBusinessUnit[]>([])
  const [activitySubjects, setActivitySubjects] = useState<DraftActivitySubject[]>([])
  const [seedTrackers, setSeedTrackers] = useState<SubjectSeedTrackers>(() =>
    createEmptySubjectSeedTrackers(),
  )
  const [isSeedingSubjects, setIsSeedingSubjects] = useState(false)
  const [proposalId, setProposalId] = useState<string | null>(null)
  const [appliedProposalId, setAppliedProposalId] = useState<string | null>(null)
  const [isSavingDraft, setIsSavingDraft] = useState(false)
  const seedTrackersRef = useRef(seedTrackers)
  const activitySubjectsRef = useRef(activitySubjects)

  useEffect(() => {
    seedTrackersRef.current = seedTrackers
  }, [seedTrackers])

  useEffect(() => {
    activitySubjectsRef.current = activitySubjects
  }, [activitySubjects])

  useEffect(() => {
    if (hydrated || proposalsQuery.isPending) {
      return
    }

    const resumeProposal = pickResumeProposal(proposalsQuery.data ?? [])
    if (!resumeProposal) {
      startTransition(() => {
        setHydrated(true)
      })
      return
    }

    const draft = hydrateDraftFromProposalPayload(resumeProposal.payload)
    const initialStep = deriveWizardStepFromState({
      businessUnits: draft.businessUnits,
      activitySubjects: draft.activitySubjects,
      proposalStatus: resumeProposal.status,
      runtimeApplied: runtimeAlreadyApplied,
    })

    startTransition(() => {
      setBusinessUnits(draft.businessUnits)
      setActivitySubjects(draft.activitySubjects)
      setSeedTrackers(draft.seedTrackers)
      setProposalId(resumeProposal.id)
      if (resumeProposal.status === 'applied') {
        setAppliedProposalId(resumeProposal.id)
      }
      setStep(initialStep)
      setMaxReachedStepIndex(stepOrder.indexOf(initialStep))
      setHydrated(true)
    })
  }, [hydrated, proposalsQuery.data, proposalsQuery.isPending, runtimeAlreadyApplied])

  useEffect(() => {
    if (step !== 'config') {
      return
    }

    let cancelled = false

    async function seedCatalogSubjects() {
      const unitsToSeed = businessUnits.filter(
        (businessUnit) =>
          businessUnit.catalog_key &&
          !seedTrackersRef.current.seededBusinessUnitClientKeys.has(businessUnit.client_key),
      )

      if (unitsToSeed.length === 0) {
        return
      }

      setIsSeedingSubjects(true)

      try {
        let nextSubjects = activitySubjectsRef.current
        let nextTrackers = seedTrackersRef.current

        for (const businessUnit of unitsToSeed) {
          const suggestions = await suggestActivitySubjects(businessUnit.catalog_key!, '', {
            limit: 200,
          })
          const merged = mergeCatalogSubjectSuggestions(
            nextSubjects,
            businessUnit,
            suggestions,
            nextTrackers,
          )
          nextSubjects = merged.activitySubjects
          nextTrackers = merged.trackers
        }

        if (!cancelled) {
          setActivitySubjects(nextSubjects)
          setSeedTrackers(nextTrackers)
        }
      } finally {
        if (!cancelled) {
          setIsSeedingSubjects(false)
        }
      }
    }

    void seedCatalogSubjects()

    return () => {
      cancelled = true
    }
  }, [businessUnits, step])

  function handleBusinessUnitsChange(nextBusinessUnits: DraftBusinessUnit[]) {
    const removedClientKeys = businessUnits
      .filter(
        (businessUnit) =>
          !nextBusinessUnits.some((item) => item.client_key === businessUnit.client_key),
      )
      .map((businessUnit) => businessUnit.client_key)

    if (removedClientKeys.length === 0) {
      setBusinessUnits(nextBusinessUnits)
      return
    }

    let nextBusinessUnitsState = nextBusinessUnits
    let nextActivitySubjects = activitySubjects
    let nextTrackers = seedTrackers

    for (const clientKey of removedClientKeys) {
      const result = removeBusinessUnitFromDraft(
        nextBusinessUnitsState,
        nextActivitySubjects,
        clientKey,
        nextTrackers,
      )
      nextBusinessUnitsState = result.businessUnits
      nextActivitySubjects = result.activitySubjects
      nextTrackers = result.trackers
    }

    setBusinessUnits(nextBusinessUnitsState)
    setActivitySubjects(nextActivitySubjects)
    setSeedTrackers(nextTrackers)
  }

  function handleExcludeCatalogSubject(businessUnitClientKey: string, catalogKey: string) {
    setSeedTrackers((current) =>
      recordExcludedCatalogSubject(current, businessUnitClientKey, catalogKey),
    )
  }

  function handleBusinessUnitDescriptionChange(clientKey: string, description: string) {
    setBusinessUnits((current) => updateBusinessUnitDescription(current, clientKey, description))
  }

  const createProposalMutation = useCreateManualOnboardingProposal(sessionId)
  const updateProposalMutation = useUpdateManualOnboardingProposal(sessionId)
  const submitProposalMutation = useSubmitManualOnboardingProposal(sessionId)
  const applyProposalMutation = useApplyOnboardingProposal(sessionId)

  const currentStepIndex = stepOrder.indexOf(step)
  const canContinueFromPoles = businessUnits.length > 0
  const canContinueFromConfig = allBusinessUnitsConfigured(businessUnits, activitySubjects)
  const isApplyStepBusy =
    createProposalMutation.isPending ||
    updateProposalMutation.isPending ||
    submitProposalMutation.isPending ||
    applyProposalMutation.isPending ||
    isSavingDraft

  const applyError =
    createProposalMutation.error ??
    updateProposalMutation.error ??
    submitProposalMutation.error ??
    applyProposalMutation.error

  async function persistDraftProposal() {
    const nextPayload = buildManualV2Payload(businessUnits, activitySubjects, seedTrackers)

    if (proposalId) {
      await updateProposalMutation.mutateAsync({
        proposalId,
        input: { payload: nextPayload },
      })
      return proposalId
    }

    const created = await createProposalMutation.mutateAsync({ payload: nextPayload })
    setProposalId(created.proposal.id)
    return created.proposal.id
  }

  async function handleApplyProposal() {
    const nextPayload = buildManualV2Payload(businessUnits, activitySubjects, seedTrackers)

    try {
      let activeProposalId = proposalId

      if (!activeProposalId) {
        const created = await createProposalMutation.mutateAsync({ payload: nextPayload })
        activeProposalId = created.proposal.id
        setProposalId(activeProposalId)
      } else {
        await updateProposalMutation.mutateAsync({
          proposalId: activeProposalId,
          input: { payload: nextPayload },
        })
      }

      const submitted = await submitProposalMutation.mutateAsync(activeProposalId)
      if (submitted.proposal.status !== 'validated') {
        return
      }

      const applied = await applyProposalMutation.mutateAsync(activeProposalId)
      setAppliedProposalId(applied.proposal.id)
      onApplied()
      goToStep('invitations')
    } catch {
      // Mutation state renders the backend error below.
    }
  }

  function goToStep(nextStep: WizardStep) {
    const nextIndex = stepOrder.indexOf(nextStep)
    setStep(nextStep)
    setMaxReachedStepIndex((current) => Math.max(current, nextIndex))
  }

  async function goToNextStep() {
    if (step === 'poles' && canContinueFromPoles) {
      setIsSavingDraft(true)
      try {
        await persistDraftProposal()
        goToStep('config')
      } finally {
        setIsSavingDraft(false)
      }
      return
    }

    if (step === 'config' && canContinueFromConfig) {
      setIsSavingDraft(true)
      try {
        await persistDraftProposal()
        goToStep('apply')
      } finally {
        setIsSavingDraft(false)
      }
    }
  }

  function goToPreviousStep() {
    if (currentStepIndex <= 0) {
      return
    }

    goToStep(stepOrder[currentStepIndex - 1]!)
  }

  function handleStepPillClick(targetStep: WizardStep, targetIndex: number) {
    if (targetIndex > maxReachedStepIndex) {
      return
    }

    goToStep(targetStep)
  }

  if (!hydrated && proposalsQuery.isPending) {
    return (
      <Card className="rounded-[1.85rem] border-[#ece5da] bg-[#fffdf9] px-4 py-8 text-sm text-muted-foreground">
        Chargement de votre progression d&apos;onboarding…
      </Card>
    )
  }

  return (
    <Card className="rounded-[1.85rem] border-[#ece5da] bg-[#fffdf9] shadow-[0_24px_52px_-40px_rgba(46,72,173,0.28)]">
      <CardHeader className="gap-3">
        <CardTitle className="text-[1.45rem] font-black tracking-[-0.05em]">
          Onboarding manuel V2
        </CardTitle>
        <CardDescription className="text-sm leading-6">
          Configurez les pôles et sujets d&apos;activité, validez la proposition, puis invitez votre
          équipe.
        </CardDescription>
        <div className="flex flex-wrap gap-2">
          {stepOrder.map((wizardStep, index) => {
            const isActive = wizardStep === step
            const isComplete = index < currentStepIndex
            const isReachable = index <= maxReachedStepIndex

            return (
              <button
                key={wizardStep}
                type="button"
                disabled={!isReachable}
                onClick={() => handleStepPillClick(wizardStep, index)}
                className={`rounded-full px-3 py-1 text-xs font-medium transition ${
                  isActive
                    ? 'bg-[color:var(--primary)] text-primary-foreground'
                    : isComplete
                      ? 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100'
                      : isReachable
                        ? 'bg-[#f3ede4] text-muted-foreground hover:bg-[#ebe2d5]'
                        : 'cursor-not-allowed bg-[#f3ede4] text-muted-foreground opacity-60'
                }`}
              >
                {index + 1}. {stepLabels[wizardStep]}
              </button>
            )
          })}
        </div>
      </CardHeader>

      <CardContent className="space-y-5">
        {step === 'poles' ? (
          <ManualOnboardingV2BuPickerStep
            businessUnits={businessUnits}
            onChange={handleBusinessUnitsChange}
          />
        ) : null}

        {step === 'config' ? (
          <ManualOnboardingV2BuConfigStep
            businessUnits={businessUnits}
            activitySubjects={activitySubjects}
            isSeedingSubjects={isSeedingSubjects}
            onBusinessUnitDescriptionChange={handleBusinessUnitDescriptionChange}
            onChange={setActivitySubjects}
            onExcludeCatalogSubject={handleExcludeCatalogSubject}
          />
        ) : null}

        {step === 'apply' ? (
          <div className="space-y-4">
            <div>
              <h3 className="text-lg font-semibold">Étape 3 — Validation et application</h3>
              <p className="text-sm leading-6 text-muted-foreground">
                La proposition technique <code>onboarding_proposal_v3</code> sera validée puis
                appliquée au runtime de l&apos;établissement.
              </p>
            </div>

            <div className="rounded-[1.25rem] border border-[#ece5da] bg-white p-4 text-sm">
              <p>
                <strong>{businessUnits.length}</strong> pôle(s) ·{' '}
                <strong>{activitySubjects.length}</strong> sujet(s)
              </p>
            </div>

            {appliedProposalId ? (
              <div className="flex items-center gap-2 rounded-[1rem] border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
                <CheckCircle2 className="size-4" />
                Proposition appliquée. Passez aux invitations.
              </div>
            ) : null}

            {applyError ? (
              <div className="space-y-2 rounded-[1rem] border border-[#f2d4cf] bg-[#fff7f6] px-4 py-3 text-sm text-[#8f3f37]">
                <p>
                  {getOnboardingErrorMessage(
                    applyError,
                    'La proposition n’a pas pu être validée ni appliquée.',
                  )}
                </p>
                <BlockerList blockers={getOnboardingErrorBlockers(applyError)} />
              </div>
            ) : null}

            <Button
              type="button"
              disabled={!canContinueFromConfig || isApplyStepBusy}
              onClick={() => {
                void handleApplyProposal()
              }}
              className="h-11 rounded-[1rem]"
            >
              {isApplyStepBusy ? (
                <>
                  <LoaderCircle className="size-4 animate-spin" />
                  Validation en cours…
                </>
              ) : (
                <>
                  Valider et appliquer
                  <ArrowRight className="size-4" />
                </>
              )}
            </Button>
          </div>
        ) : null}

        {step === 'invitations' ? (
          <ManualOnboardingV2InvitationsStep
            activationSummary={activationSummary}
            activationSummaryError={activationSummaryError}
            establishmentId={establishmentId}
            isActivationSummaryLoading={isActivationSummaryLoading}
            onRetryActivationSummary={onRetryActivationSummary}
            sessionId={sessionId}
          />
        ) : null}

        {step !== 'apply' && step !== 'invitations' ? (
          <div className="flex flex-col gap-3 sm:flex-row sm:justify-between">
            <Button
              type="button"
              variant="outline"
              disabled={currentStepIndex === 0}
              onClick={goToPreviousStep}
              className="h-11 rounded-[1rem] border-[#e7dfd1] bg-[#fffaf2]"
            >
              <ArrowLeft className="size-4" />
              Retour
            </Button>
            <Button
              type="button"
              disabled={
                isSavingDraft ||
                (step === 'poles' && !canContinueFromPoles) ||
                (step === 'config' && (!canContinueFromConfig || isSeedingSubjects))
              }
              onClick={() => {
                void goToNextStep()
              }}
              className="h-11 rounded-[1rem]"
            >
              {isSavingDraft ? (
                <>
                  <LoaderCircle className="size-4 animate-spin" />
                  Enregistrement…
                </>
              ) : (
                <>
                  Continuer
                  <ArrowRight className="size-4" />
                </>
              )}
            </Button>
          </div>
        ) : null}

        {step === 'invitations' ? (
          <Button
            type="button"
            variant="outline"
            onClick={() => goToStep('poles')}
            className="h-11 rounded-[1rem] border-[#e7dfd1] bg-[#fffaf2]"
          >
            <ArrowLeft className="size-4" />
            Revenir aux pôles
          </Button>
        ) : null}
      </CardContent>
    </Card>
  )
}
