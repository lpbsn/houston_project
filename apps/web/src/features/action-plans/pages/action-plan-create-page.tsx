import { startTransition, useEffect, useMemo, useState } from 'react'
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
import { Textarea } from '@/components/ui/textarea'
import { ActionLinkedSignalCard } from '@/features/action-plans/components/action-linked-signal-card'
import { ActionLinkedSignalStrip } from '@/features/action-plans/components/action-linked-signal-strip'
import { useBusinessUnitTreeQuery } from '@/features/auth/hooks'
import { getBootstrapPermissionHints } from '@/features/auth/lib/bootstrap-permission-hints'
import { TerrainFeedback } from '@/components/domain/terrain-feedback'
import { SignalsApiError } from '@/features/signals/api'
import { SignalClassificationBadges } from '@/features/signals/components/signal-classification-badges'
import { useSignalDetailQuery } from '@/features/signals/hooks'
import { resolveApiErrorMessage } from '@/lib/error-message'
import { terrainBrandAction } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

import { ActionPlanEventPlanningForm } from '../components/action-plan-event-planning-form'
import {
  PlanningOptionRow,
  type PlanningOptionPickerTarget,
} from '../components/planning/planning-option-row'
import { ActionPlanTaskDraftEditor } from '../components/action-plan-task-draft-editor'
import { useActionPlanCreateSubmit } from '../hooks/use-action-plan-create-submit'
import { useActionPlanEditSubmit } from '../hooks/use-action-plan-edit-submit'
import { useActionPlanDetailQuery } from '../hooks'
import {
  type ActionPlanCreateMode,
  resolveActionPlanCreateModeConfig,
} from '../lib/action-plan-create-mode'
import { canCreateSignalLinkedActionPlanFromSignalHints } from '../lib/action-plan-management-access'
import {
  actionPlanTaskTemplateToDraft,
  createActionPlanAssigneeDraft,
  type ActionPlanCreateFormValues,
  type ActionPlanTaskDraft,
} from '../lib/action-plan-form-validation'
import {
  createActionPlanEventPlanningDraft,
  toCreateFormPlanningSlice,
  type ActionPlanEventPlanningDraft,
} from '../lib/action-plan-event-planning-form'
import { resolveVisibleBusinessUnits } from '../lib/resolve-visible-business-units'
import { canShowActionPlanUpdate } from '../lib/action-plan-permission-hints'

const SIGNAL_LINKED_PERMISSION_MESSAGE =
  "Vous n'avez pas la permission de créer un plan d'action."

type ActionPlanCreatePageProps = {
  mode?: ActionPlanCreateMode
  backPath?: string
  signalId?: string
  actionPlanId?: string
}

export function ActionPlanCreatePage({
  mode = 'catalog',
  backPath = '/action-plans',
  signalId,
  actionPlanId,
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
  const isTemplateEdit = mode === 'template-edit'

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

  const templateDetailQuery = useActionPlanDetailQuery(
    establishmentId,
    isTemplateEdit ? (actionPlanId ?? null) : null,
  )

  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [pilotBusinessUnitId, setPilotBusinessUnitId] = useState('')
  const [requiresValidation, setRequiresValidation] = useState(
    modeConfig.defaultRequiresValidation,
  )
  const [saveToLibrary, setSaveToLibrary] = useState(modeConfig.defaultSaveToLibrary)
  const [tasks, setTasks] = useState<ActionPlanTaskDraft[]>([])
  const [planningDraft, setPlanningDraft] = useState<ActionPlanEventPlanningDraft>(
    createActionPlanEventPlanningDraft,
  )
  const [openPilotPicker, setOpenPilotPicker] = useState<PlanningOptionPickerTarget>(null)
  const [isTemplateHydrated, setIsTemplateHydrated] = useState(false)

  useEffect(() => {
    if (!isTemplateEdit || !templateDetailQuery.data || isTemplateHydrated) {
      return
    }
    const plan = templateDetailQuery.data
    startTransition(() => {
      setTitle(plan.title)
      setDescription(plan.description)
      setPilotBusinessUnitId(plan.pilot_business_unit.id)
      setRequiresValidation(plan.requires_validation)
      setTasks(plan.tasks.map(actionPlanTaskTemplateToDraft))
      setIsTemplateHydrated(true)
    })
  }, [isTemplateEdit, isTemplateHydrated, templateDetailQuery.data])

  const businessUnitQuery = useBusinessUnitTreeQuery(establishmentId, { staleTime: 60_000 })
  const businessUnits = useMemo(
    () =>
      (businessUnitQuery.data?.business_units ?? []).map((unit) => ({
        id: unit.id,
        label: unit.specific_name,
      })),
    [businessUnitQuery.data?.business_units],
  )

  const visibleBusinessUnits = useMemo(
    () =>
      resolveVisibleBusinessUnits({
        role,
        scopes: activeMembership?.scopes,
        businessUnits,
        filterByScope: modeConfig.filterBusinessUnitsByScope,
      }),
    [
      activeMembership?.scopes,
      businessUnits,
      modeConfig.filterBusinessUnitsByScope,
      role,
    ],
  )

  const signalPilotBusinessUnitId = useMemo(() => {
    if (!modeConfig.lockPilotBusinessUnit) {
      return ''
    }
    return signalDetailQuery.data?.responsible_business_unit_id ?? ''
  }, [modeConfig.lockPilotBusinessUnit, signalDetailQuery.data])

  const resolvedPilotBusinessUnitId = useMemo(() => {
    if (isTemplateEdit && templateDetailQuery.data) {
      return templateDetailQuery.data.pilot_business_unit.id
    }
    if (modeConfig.lockPilotBusinessUnit) {
      return signalPilotBusinessUnitId
    }
    return pilotBusinessUnitId || visibleBusinessUnits[0]?.id || ''
  }, [
    isTemplateEdit,
    modeConfig.lockPilotBusinessUnit,
    pilotBusinessUnitId,
    signalPilotBusinessUnitId,
    templateDetailQuery.data,
    visibleBusinessUnits,
  ])

  const pilotBusinessUnitOptions = useMemo(
    () => visibleBusinessUnits.map((unit) => ({ value: unit.id, label: unit.label })),
    [visibleBusinessUnits],
  )

  const canCrossPole = modeConfig.canDefineCrossPoleTasks

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
      tasks,
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
      tasks,
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

  const templateEditBackPath =
    isTemplateEdit && actionPlanId ? `/action-plans/${actionPlanId}` : backPath

  const {
    submit: submitEdit,
    fieldErrors: editFieldErrors,
    submitError: editSubmitError,
    isSubmitting: isEditSubmitting,
  } = useActionPlanEditSubmit({
    establishmentId: establishmentId ?? '',
    actionPlanId: actionPlanId ?? '',
    canDefineCrossPoleTasks: canCrossPole,
    onNavigate: navigate,
  })

  const resolvedFieldErrors = isTemplateEdit ? editFieldErrors : fieldErrors
  const resolvedSubmitError = isTemplateEdit ? editSubmitError : submitError
  const resolvedIsSubmitting = isTemplateEdit ? isEditSubmitting : isSubmitting

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

  if (isTemplateEdit) {
    if (!actionPlanId) {
      return (
        <TerrainErrorState
          className="mx-3 mt-3"
          message="Plan introuvable."
          onRetry={() => navigate('/action-plans')}
        />
      )
    }

    if (templateDetailQuery.isLoading || !isTemplateHydrated) {
      return (
        <div className="flex items-center justify-center py-16 text-[#7D7B75]">
          <LoaderCircle className="h-6 w-6 animate-spin" />
        </div>
      )
    }

    if (templateDetailQuery.isError || !templateDetailQuery.data) {
      return (
        <TerrainErrorState
          className="mx-3 mt-3"
          message="Ce plan est introuvable ou inaccessible."
          onRetry={() => void templateDetailQuery.refetch()}
        />
      )
    }

    if (!canShowActionPlanUpdate(templateDetailQuery.data.permission_hints)) {
      return (
        <TerrainErrorState
          className="mx-3 mt-3"
          message="Vous n’avez pas la permission de modifier ce plan."
          onRetry={() => navigate(templateEditBackPath)}
        />
      )
    }
  }

  if (!modeConfig.canAccess && !isTemplateEdit) {
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

  const showPlanningForm = !isTemplateEdit
  const showToggleSection = isTemplateEdit
    ? modeConfig.showValidationToggle
    : modeConfig.showLibraryToggle || modeConfig.showValidationToggle
  const submitLabel = isTemplateEdit
    ? 'Enregistrer les modifications'
    : saveToLibrary
      ? 'Enregistrer dans la bibliothèque'
      : 'Créer le plan d’action'

  async function handlePrimarySubmit() {
    await submit(formValues, { ...planningDraft, assignees: effectiveAssignees })
  }

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
              className="h-11 border-[#E8E6DF]"
            />
            {fieldErrors.title ? (
              <p className="mt-1 text-xs text-destructive">{resolvedFieldErrors.title}</p>
            ) : null}
          </div>
          <div>
            <TerrainFieldLabel>Description</TerrainFieldLabel>
            <Textarea
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              className="min-h-20 border-[#E8E6DF]"
            />
          </div>
          <PlanningOptionRow
            rowId="pilot-business-unit"
            label="Pôle d'activité pilote"
            value={pilotBusinessUnitId}
            displayValue={
              modeConfig.lockPilotBusinessUnit
                ? (signalDetail?.responsible_business_unit_label ?? '—')
                : pilotBusinessUnitOptions.find((option) => option.value === resolvedPilotBusinessUnitId)
                    ?.label
            }
            options={pilotBusinessUnitOptions}
            disabled={modeConfig.lockPilotBusinessUnit}
            openPicker={openPilotPicker}
            onOpenPickerChange={setOpenPilotPicker}
            onChange={setPilotBusinessUnitId}
            error={resolvedFieldErrors.pilotBusinessUnitId}
          />
        </TerrainCard>

        {showToggleSection ? (
          <section className="space-y-2">
            <TerrainSectionLabel>Options</TerrainSectionLabel>
            <TerrainCard className="divide-y divide-[#E8E6DF] p-0">
              {modeConfig.showValidationToggle ? (
                <TerrainSwitch
                  label="Validation requise"
                  checked={requiresValidation}
                  onCheckedChange={setRequiresValidation}
                />
              ) : null}
              {modeConfig.showLibraryToggle ? (
                <TerrainSwitch
                  label="Enregistrer dans la bibliothèque"
                  checked={saveToLibrary}
                  onCheckedChange={setSaveToLibrary}
                />
              ) : null}
            </TerrainCard>
          </section>
        ) : null}

        <ActionPlanTaskDraftEditor
          tasks={tasks}
          establishmentId={establishmentId ?? ''}
          pilotBusinessUnitId={resolvedPilotBusinessUnitId}
          canDefineCrossPoleTasks={canCrossPole}
          staffMode={modeConfig.showStaffSelfAssignee}
          businessUnits={visibleBusinessUnits}
          onTasksChange={setTasks}
        />
        {resolvedFieldErrors.tasks ? (
          <p className="text-xs text-destructive">{resolvedFieldErrors.tasks}</p>
        ) : null}

        {showPlanningForm ? (
          <ActionPlanEventPlanningForm
            draft={{ ...planningDraft, assignees: effectiveAssignees }}
            config={{
              canEditAssignees: modeConfig.showAssigneeSheet,
              canSchedule: modeConfig.showScheduleSection,
              staffMode: modeConfig.showStaffSelfAssignee,
              showAdvancedChronology: modeConfig.showAssigneeSheet,
              hideAssignees: false,
              staffDisplayName,
              planningPersisted: saveToLibrary ? false : undefined,
              assigneeActionsEnabled: false,
            }}
            establishmentId={establishmentId}
            pilotBusinessUnitId={resolvedPilotBusinessUnitId}
            fieldErrors={resolvedFieldErrors}
            onDraftChange={(next) => {
              if (modeConfig.showStaffSelfAssignee) {
                setPlanningDraft({ ...next, assignees: effectiveAssignees })
                return
              }
              setPlanningDraft(next)
            }}
          />
        ) : null}

        {resolvedSubmitError ? (
          <TerrainFeedback variant="error" message={resolvedSubmitError} />
        ) : null}
      </div>

      <TerrainStickyFooter>
        {isTemplateEdit ? (
          <div className="flex gap-2">
            <Button
              type="button"
              variant="outline"
              className="h-11 flex-1 rounded-xl"
              disabled={resolvedIsSubmitting}
              onClick={() => navigate(templateEditBackPath)}
            >
              Retour
            </Button>
            <Button
              type="button"
              className={cn(
                'h-11 flex-1 rounded-xl text-white',
                terrainBrandAction.bg,
                terrainBrandAction.hover,
              )}
              disabled={resolvedIsSubmitting}
              onClick={() => void submitEdit(formValues)}
            >
              {submitLabel}
            </Button>
          </div>
        ) : (
          <Button
            type="button"
            className={cn(
              'h-11 w-full rounded-xl text-white',
              terrainBrandAction.bg,
              terrainBrandAction.hover,
            )}
            disabled={resolvedIsSubmitting}
            onClick={() => void handlePrimarySubmit()}
          >
            {submitLabel}
          </Button>
        )}
      </TerrainStickyFooter>
    </div>
  )
}
