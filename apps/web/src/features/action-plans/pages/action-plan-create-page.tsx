import { useMemo, useState } from 'react'
import { LoaderCircle } from 'lucide-react'

import { useAppRoute } from '@/app/app-routes'
import { useAuth } from '@/app/auth-provider'
import {
  TerrainCard,
  TerrainErrorState,
  TerrainFieldLabel,
  TerrainSectionLabel,
  TerrainStickyFooter,
} from '@/components/ui/terrain'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ActionLinkedSignalCard } from '@/features/action-plans/components/action-linked-signal-card'
import { ActionLinkedSignalStrip } from '@/features/action-plans/components/action-linked-signal-strip'
import { useBusinessUnitTreeQuery } from '@/features/auth/hooks'
import { getBootstrapPermissionHints } from '@/features/auth/lib/bootstrap-permission-hints'
import { TerrainFeedback } from '@/components/domain/terrain-feedback'
import { SignalsApiError } from '@/features/signals/api'
import { SignalClassificationBadges } from '@/features/signals/components/signal-classification-badges'
import { useSignalDetailQuery } from '@/features/signals/hooks'
import { resolveApiErrorMessage } from '@/lib/error-message'
import { terrain } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

import { ActionPlanAssigneeChronologySheet } from '../components/action-plan-assignee-chronology-sheet'
import {
  ActionPlanTaskDraftEditor,
} from '../components/action-plan-task-draft-editor'
import { useActionPlanCreateSubmit } from '../hooks/use-action-plan-create-submit'
import {
  type ActionPlanCreateMode,
  resolveActionPlanCreateModeConfig,
} from '../lib/action-plan-create-mode'
import { canCreateSignalLinkedActionPlanFromSignalHints } from '../lib/action-plan-management-access'
import {
  createActionPlanAssigneeDraft,
  createActionPlanTaskDraft,
  type ActionPlanAssigneeDraft,
  type ActionPlanCreateFormValues,
} from '../lib/action-plan-form-validation'

const SIGNAL_LINKED_PERMISSION_MESSAGE =
  "Vous n'avez pas la permission de créer un plan d'action."

type ActionPlanCreatePageProps = {
  mode?: ActionPlanCreateMode
  backPath?: string
  signalId?: string
}

export function ActionPlanCreatePage({
  mode = 'catalog',
  backPath = '/action-plans',
  signalId,
}: ActionPlanCreatePageProps) {
  const { navigate } = useAppRoute()
  const auth = useAuth()
  const { activeMembership, bootstrap } = auth
  const establishmentId = activeMembership?.establishment_id ?? null
  const role = activeMembership?.role ?? null
  const membershipId = activeMembership?.id
  const permissionHints = getBootstrapPermissionHints(bootstrap)
  const canCreateActionPlan = permissionHints.can_create_action_plan === true
  const isSignalLinked = mode === 'signal-linked'

  const modeConfig = useMemo(
    () =>
      resolveActionPlanCreateModeConfig({
        mode,
        role,
        canCreateActionPlan,
        membershipId,
      }),
    [mode, role, canCreateActionPlan, membershipId],
  )

  const signalDetailQuery = useSignalDetailQuery(
    establishmentId,
    isSignalLinked ? (signalId ?? null) : null,
  )

  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [pilotBusinessUnitId, setPilotBusinessUnitId] = useState('')
  const [requiresValidation, setRequiresValidation] = useState(
    modeConfig.defaultRequiresValidation,
  )
  const [saveToLibrary, setSaveToLibrary] = useState(modeConfig.defaultSaveToLibrary)
  const [useSharedChronology, setUseSharedChronology] = useState(true)
  const [sharedStartAt, setSharedStartAt] = useState('')
  const [sharedEndAt, setSharedEndAt] = useState('')
  const [sharedVisibleFrom, setSharedVisibleFrom] = useState('')
  const [tasks, setTasks] = useState([createActionPlanTaskDraft()])
  const [assignees, setAssignees] = useState<ActionPlanAssigneeDraft[]>([])
  const [assigneeSheetOpen, setAssigneeSheetOpen] = useState(false)

  const businessUnitQuery = useBusinessUnitTreeQuery(establishmentId, { staleTime: 60_000 })
  const businessUnits = useMemo(
    () => businessUnitQuery.data?.business_units ?? [],
    [businessUnitQuery.data?.business_units],
  )

  const visibleBusinessUnits = useMemo(() => {
    if (!modeConfig.filterBusinessUnitsByScope) {
      return businessUnits
    }
    const scopes = activeMembership?.scopes ?? []
    if (scopes.length === 0) {
      return businessUnits
    }
    return businessUnits.filter((unit) =>
      scopes.some(
        (scope) => scope.scope_type === 'business_unit' && scope.scope_id === unit.id,
      ),
    )
  }, [activeMembership?.scopes, businessUnits, modeConfig.filterBusinessUnitsByScope])

  const resolvedPilotBusinessUnitId =
    pilotBusinessUnitId || visibleBusinessUnits[0]?.id || ''

  const canCrossPole = modeConfig.canDefineCrossPoleTasks

  const resolvedTasks = useMemo(() => {
    if (!resolvedPilotBusinessUnitId) {
      return tasks
    }
    return tasks.map((task) => ({
      ...task,
      businessUnitId: task.businessUnitId || resolvedPilotBusinessUnitId,
    }))
  }, [resolvedPilotBusinessUnitId, tasks])

  const staffDisplayName = bootstrap?.user?.username ?? 'Moi'

  const effectiveAssignees = useMemo(() => {
    if (modeConfig.showStaffSelfAssignee && membershipId && resolvedPilotBusinessUnitId) {
      return [
        createActionPlanAssigneeDraft({
          membershipId,
          businessUnitId: resolvedPilotBusinessUnitId,
          displayName: staffDisplayName,
        }),
      ]
    }
    return assignees
  }, [
    assignees,
    membershipId,
    modeConfig.showStaffSelfAssignee,
    resolvedPilotBusinessUnitId,
    staffDisplayName,
  ])

  const formValues = useMemo<ActionPlanCreateFormValues>(
    () => ({
      title,
      description,
      pilotBusinessUnitId: resolvedPilotBusinessUnitId,
      requiresValidation,
      saveToLibrary,
      useSharedChronology,
      sharedStartAt,
      sharedEndAt,
      sharedVisibleFrom,
      tasks: resolvedTasks,
      assignees: effectiveAssignees,
      sourceSignalId: isSignalLinked ? signalId : undefined,
    }),
    [
      effectiveAssignees,
      description,
      resolvedPilotBusinessUnitId,
      requiresValidation,
      saveToLibrary,
      sharedEndAt,
      sharedStartAt,
      sharedVisibleFrom,
      resolvedTasks,
      title,
      useSharedChronology,
      isSignalLinked,
      signalId,
    ],
  )

  const staffExecutionMode =
    modeConfig.showStaffSelfAssignee && membershipId && resolvedPilotBusinessUnitId
      ? { membershipId, pilotBusinessUnitId: resolvedPilotBusinessUnitId }
      : undefined

  const { submit, fieldErrors, submitError, isSubmitting } = useActionPlanCreateSubmit({
    establishmentId: establishmentId ?? '',
    canDefineCrossPoleTasks: canCrossPole,
    staffExecutionMode,
    onNavigate: navigate,
  })

  if (!establishmentId) {
    return null
  }

  if (isSignalLinked && !signalId) {
    return (
      <TerrainErrorState
        className="mx-3 mt-3"
        message="Signal introuvable."
        onRetry={() => navigate('/signals')}
      />
    )
  }

  if (!modeConfig.canAccess) {
    return (
      <TerrainErrorState
        className="mx-3 mt-3"
        message={
          isSignalLinked
            ? SIGNAL_LINKED_PERMISSION_MESSAGE
            : 'Vous n’avez pas accès à la création de plans d’action.'
        }
        onRetry={() => navigate(backPath)}
      />
    )
  }

  if (isSignalLinked) {
    if (signalDetailQuery.isLoading) {
      return (
        <div className="flex items-center justify-center py-16 text-[#7D7B75]">
          <LoaderCircle className="h-6 w-6 animate-spin" />
        </div>
      )
    }

    if (signalDetailQuery.isError || !signalDetailQuery.data) {
      return (
        <TerrainErrorState
          className="mx-3 mt-3"
          message={resolveApiErrorMessage(
            signalDetailQuery.error,
            SignalsApiError,
            'Une erreur est survenue.',
          )}
          onRetry={() => void signalDetailQuery.refetch()}
        />
      )
    }

    if (!canCreateSignalLinkedActionPlanFromSignalHints(signalDetailQuery.data.permission_hints)) {
      return (
        <TerrainErrorState
          className="mx-3 mt-3"
          message={SIGNAL_LINKED_PERMISSION_MESSAGE}
          onRetry={() => navigate(backPath)}
        />
      )
    }
  }

  const signalDetail = isSignalLinked ? signalDetailQuery.data : null

  const showAssigneeSection = !saveToLibrary && modeConfig.showAssigneeSheet
  const showToggleSection = modeConfig.showLibraryToggle || modeConfig.showValidationToggle

  return (
    <div className="flex min-h-full flex-col">
      {signalDetail ? (
        <ActionLinkedSignalStrip>
          <ActionLinkedSignalCard
            title={signalDetail.title}
            locationText={signalDetail.location_text || null}
          />
        </ActionLinkedSignalStrip>
      ) : null}

      <div className="space-y-3 px-3 pb-28 pt-2">
        {signalDetail ? (
          <section className="flex flex-col gap-1.5">
            <TerrainSectionLabel>Classification héritée du signal</TerrainSectionLabel>
            <TerrainCard className="px-3 py-2.5">
              <SignalClassificationBadges signal={signalDetail} />
            </TerrainCard>
          </section>
        ) : null}

        <TerrainCard className="space-y-3">
          <div>
            <TerrainFieldLabel>Titre</TerrainFieldLabel>
            <Input
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              className="h-11 border-[#E8E6DF] text-sm"
            />
            {fieldErrors.title ? (
              <p className="mt-1 text-xs text-destructive">{fieldErrors.title}</p>
            ) : null}
          </div>
          <div>
            <TerrainFieldLabel>Description</TerrainFieldLabel>
            <textarea
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              className="min-h-20 w-full rounded-xl border border-[#E8E6DF] px-3 py-2 text-sm"
            />
          </div>
          <div>
            <TerrainFieldLabel>Pôle d&apos;activité pilote</TerrainFieldLabel>
            <select
              value={resolvedPilotBusinessUnitId}
              onChange={(event) => setPilotBusinessUnitId(event.target.value)}
              className="h-11 w-full rounded-xl border border-[#E8E6DF] px-3 text-sm"
            >
              {visibleBusinessUnits.map((unit) => (
                <option key={unit.id} value={unit.id}>
                  {unit.label}
                </option>
              ))}
            </select>
            {fieldErrors.pilotBusinessUnitId ? (
              <p className="mt-1 text-xs text-destructive">{fieldErrors.pilotBusinessUnitId}</p>
            ) : null}
          </div>
        </TerrainCard>

        <ActionPlanTaskDraftEditor
          tasks={resolvedTasks}
          pilotBusinessUnitId={resolvedPilotBusinessUnitId}
          canDefineCrossPoleTasks={canCrossPole}
          businessUnits={visibleBusinessUnits}
          onTasksChange={setTasks}
        />
        {fieldErrors.tasks ? (
          <p className="text-xs text-destructive">{fieldErrors.tasks}</p>
        ) : null}

        {showAssigneeSection ? (
          <section className="space-y-2">
            <TerrainSectionLabel>Assignés et chronologie</TerrainSectionLabel>
            <Button
              type="button"
              variant="outline"
              className="h-11 w-full rounded-xl"
              onClick={() => setAssigneeSheetOpen(true)}
            >
              Configurer les assignés
            </Button>
            {fieldErrors.assignees ? (
              <p className="text-xs text-destructive">{fieldErrors.assignees}</p>
            ) : null}
          </section>
        ) : null}

        {modeConfig.showStaffSelfAssignee ? (
          <section className="space-y-2">
            <TerrainSectionLabel>Assigné</TerrainSectionLabel>
            <TerrainCard className="px-3 py-2.5 text-sm text-[#1a1a1a]">{staffDisplayName}</TerrainCard>
            {fieldErrors.assignees ? (
              <p className="text-xs text-destructive">{fieldErrors.assignees}</p>
            ) : null}
          </section>
        ) : null}

        {showToggleSection ? (
          <TerrainCard className="space-y-3">
            {modeConfig.showValidationToggle ? (
              <label className="flex items-center justify-between gap-3 text-sm text-[#1a1a1a]">
                <span>Validation requise</span>
                <input
                  type="checkbox"
                  checked={requiresValidation}
                  onChange={(event) => setRequiresValidation(event.target.checked)}
                />
              </label>
            ) : null}
            {modeConfig.showLibraryToggle ? (
              <>
                <label className="flex items-center justify-between gap-3 text-sm text-[#1a1a1a]">
                  <span>Enregistrer dans la bibliothèque</span>
                  <input
                    type="checkbox"
                    checked={saveToLibrary}
                    onChange={(event) => setSaveToLibrary(event.target.checked)}
                  />
                </label>
                <p className={cn('text-xs', terrain.muted)}>
                  Un modèle bibliothèque est réutilisable sans assignés à la création.
                </p>
              </>
            ) : null}
          </TerrainCard>
        ) : null}

        {submitError ? <TerrainFeedback variant="error" message={submitError} /> : null}
      </div>

      <TerrainStickyFooter>
        <Button
          type="button"
          className="h-11 w-full rounded-xl"
          disabled={isSubmitting}
          onClick={() => void submit(formValues)}
        >
          {saveToLibrary ? 'Enregistrer dans la bibliothèque' : 'Créer le plan d’action'}
        </Button>
      </TerrainStickyFooter>

      {showAssigneeSection ? (
        <ActionPlanAssigneeChronologySheet
          open={assigneeSheetOpen}
          establishmentId={establishmentId}
          pilotBusinessUnitId={resolvedPilotBusinessUnitId}
          assignees={assignees}
          useSharedChronology={useSharedChronology}
          sharedStartAt={sharedStartAt}
          sharedEndAt={sharedEndAt}
          sharedVisibleFrom={sharedVisibleFrom}
          onAssigneesChange={setAssignees}
          onUseSharedChronologyChange={setUseSharedChronology}
          onSharedStartAtChange={setSharedStartAt}
          onSharedEndAtChange={setSharedEndAt}
          onSharedVisibleFromChange={setSharedVisibleFrom}
          onClose={() => setAssigneeSheetOpen(false)}
          onConfirm={() => setAssigneeSheetOpen(false)}
        />
      ) : null}
    </div>
  )
}
