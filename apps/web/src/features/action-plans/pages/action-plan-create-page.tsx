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
  TerrainSwitch,
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

import { ActionPlanEventPlanningForm } from '../components/action-plan-event-planning-form'
import {
  PlanningOptionRow,
  type PlanningOptionPickerTarget,
} from '../components/planning/planning-option-row'
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
  type ActionPlanCreateFormValues,
} from '../lib/action-plan-form-validation'
import {
  createActionPlanEventPlanningDraft,
  toCreateFormPlanningSlice,
  type ActionPlanEventPlanningDraft,
} from '../lib/action-plan-event-planning-form'
import { isActionPlanScheduleConfigured } from '../lib/action-plan-schedule-form'

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
  const canCreateCatalogActionPlan = permissionHints.can_create_catalog_action_plan === true
  const isSignalLinked = mode === 'signal-linked'

  const modeConfig = useMemo(
    () =>
      resolveActionPlanCreateModeConfig({
        mode,
        role,
        canCreateActionPlan,
        canCreateCatalogActionPlan,
        membershipId,
      }),
    [mode, role, canCreateActionPlan, canCreateCatalogActionPlan, membershipId],
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
  const [tasks, setTasks] = useState([createActionPlanTaskDraft()])
  const [planningDraft, setPlanningDraft] = useState<ActionPlanEventPlanningDraft>(
    createActionPlanEventPlanningDraft,
  )
  const [openPilotPicker, setOpenPilotPicker] = useState<PlanningOptionPickerTarget>(null)

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

  const signalPilotBusinessUnitId = useMemo(() => {
    if (!modeConfig.lockPilotBusinessUnit) {
      return ''
    }
    const responsibleKey = signalDetailQuery.data?.responsible_business_unit_key
    if (!responsibleKey) {
      return ''
    }
    return businessUnits.find((unit) => unit.key === responsibleKey)?.id ?? ''
  }, [businessUnits, modeConfig.lockPilotBusinessUnit, signalDetailQuery.data])

  const resolvedPilotBusinessUnitId = useMemo(() => {
    if (modeConfig.lockPilotBusinessUnit) {
      return signalPilotBusinessUnitId
    }
    return pilotBusinessUnitId || visibleBusinessUnits[0]?.id || ''
  }, [
    modeConfig.lockPilotBusinessUnit,
    pilotBusinessUnitId,
    signalPilotBusinessUnitId,
    visibleBusinessUnits,
  ])

  const pilotBusinessUnitOptions = useMemo(
    () => visibleBusinessUnits.map((unit) => ({ value: unit.id, label: unit.label })),
    [visibleBusinessUnits],
  )

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
    return planningDraft.assignees
  }, [
    membershipId,
    modeConfig.showStaffSelfAssignee,
    planningDraft.assignees,
    resolvedPilotBusinessUnitId,
    staffDisplayName,
  ])

  const planningSlice = useMemo(
    () =>
      toCreateFormPlanningSlice({
        ...planningDraft,
        assignees: effectiveAssignees,
      }),
    [effectiveAssignees, planningDraft],
  )

  const formValues = useMemo<ActionPlanCreateFormValues>(
    () => ({
      title,
      description,
      pilotBusinessUnitId: resolvedPilotBusinessUnitId,
      requiresValidation,
      saveToLibrary,
      useSharedChronology: planningSlice.useSharedChronology,
      sharedStartAt: planningSlice.sharedStartAt,
      sharedEndAt: planningSlice.sharedEndAt,
      sharedVisibleFrom: planningSlice.sharedVisibleFrom,
      tasks: resolvedTasks,
      assignees: effectiveAssignees,
      schedule: planningSlice.schedule,
      sourceSignalId: isSignalLinked ? signalId : undefined,
    }),
    [
      effectiveAssignees,
      description,
      resolvedPilotBusinessUnitId,
      requiresValidation,
      saveToLibrary,
      planningSlice,
      resolvedTasks,
      title,
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

  const scheduleConfigured = isActionPlanScheduleConfigured(planningSlice.schedule)
  const showPlanningForm =
    !saveToLibrary || modeConfig.showStaffSelfAssignee || modeConfig.showScheduleSection
  const showToggleSection = modeConfig.showLibraryToggle || modeConfig.showValidationToggle
  const submitLabel = scheduleConfigured
    ? saveToLibrary
      ? 'Enregistrer et planifier'
      : 'Créer et planifier'
    : saveToLibrary
      ? 'Enregistrer dans la bibliothèque'
      : 'Créer le plan d’action'

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
          <PlanningOptionRow
            rowId="pilot-business-unit"
            label="Pôle d'activité pilote"
            value={resolvedPilotBusinessUnitId}
            displayValue={
              modeConfig.lockPilotBusinessUnit
                ? (signalDetail?.responsible_business_unit_label ?? '—')
                : undefined
            }
            options={pilotBusinessUnitOptions}
            disabled={modeConfig.lockPilotBusinessUnit}
            openPicker={openPilotPicker}
            onOpenPickerChange={setOpenPilotPicker}
            onChange={setPilotBusinessUnitId}
            error={fieldErrors.pilotBusinessUnitId}
          />
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

        {showPlanningForm ? (
          <ActionPlanEventPlanningForm
            draft={{ ...planningDraft, assignees: effectiveAssignees }}
            config={{
              canEditAssignees: !saveToLibrary && modeConfig.showAssigneeSheet,
              canSchedule: modeConfig.showScheduleSection,
              staffMode: modeConfig.showStaffSelfAssignee,
              showAdvancedChronology: !saveToLibrary && modeConfig.showAssigneeSheet,
              hideAssignees: saveToLibrary,
              staffDisplayName,
            }}
            establishmentId={establishmentId}
            pilotBusinessUnitId={resolvedPilotBusinessUnitId}
            fieldErrors={fieldErrors}
            onDraftChange={(next) => {
              if (modeConfig.showStaffSelfAssignee) {
                setPlanningDraft({ ...next, assignees: effectiveAssignees })
                return
              }
              setPlanningDraft(next)
            }}
          />
        ) : null}

        {showToggleSection ? (
          <TerrainCard className="divide-y divide-[#E8E6DF] p-0">
            {modeConfig.showValidationToggle ? (
              <TerrainSwitch
                label="Validation requise"
                checked={requiresValidation}
                onCheckedChange={setRequiresValidation}
              />
            ) : null}
            {modeConfig.showLibraryToggle ? (
              <div className="px-4 py-3.5">
                <TerrainSwitch
                  label="Enregistrer dans la bibliothèque"
                  checked={saveToLibrary}
                  onCheckedChange={setSaveToLibrary}
                />
                <p className={cn('mt-2 text-xs', terrain.muted)}>
                  Un modèle bibliothèque est réutilisable sans assignés à la création.
                </p>
              </div>
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
          onClick={() =>
            void submit(formValues, { ...planningDraft, assignees: effectiveAssignees })
          }
        >
          {submitLabel}
        </Button>
      </TerrainStickyFooter>
    </div>
  )
}
