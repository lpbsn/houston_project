import { startTransition, useEffect, useMemo, useRef, useState, type FormEvent } from 'react'
import { LoaderCircle } from 'lucide-react'

import { useAppRoute } from '@/app/app-routes'
import { useAuth } from '@/app/auth-provider'
import { TerrainFeedback } from '@/components/domain/terrain-feedback'
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
import { useBusinessUnitTreeQuery } from '@/features/auth/hooks'
import { terrainBrandAction } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

import { ActionPlanEventPlanningForm } from '../components/action-plan-event-planning-form'
import { ActionPlanTaskDraftEditor } from '../components/action-plan-task-draft-editor'
import { ActionPlanTaskReadOnlyRow } from '../components/action-plan-task-read-only-row'
import { PlanningOptionRow } from '../components/planning/planning-option-row'
import { useActionPlanExecutionDetailQuery } from '../hooks'
import { useActionPlanExecutionEditSubmit } from '../hooks/use-action-plan-execution-edit-submit'
import { formatActionPlanTaskStatusLabel } from '../lib/action-plan-display'
import {
  hydrateActionPlanExecutionEditForm,
  type ActionPlanExecutionEditFormValues,
} from '../lib/action-plan-execution-edit-form'
import type { ActionPlanEventPlanningDraft } from '../lib/action-plan-event-planning-form'
import { taskIdsNeedingAdvancedExpand } from '../lib/action-plan-field-errors'
import { guideToFirstActionPlanFieldError } from '../lib/action-plan-form-guidance'
import { canDefineCrossPoleTasks } from '../lib/action-plan-management-access'
import { canShowActionPlanExecutionUpdate } from '../lib/action-plan-permission-hints'
import type { ActionPlanTaskDraft } from '../lib/action-plan-form-validation'
import { resolveVisibleBusinessUnits } from '../lib/resolve-visible-business-units'

type ActionPlanExecutionEditPageProps = {
  executionId: string
}

export function ActionPlanExecutionEditPage({ executionId }: ActionPlanExecutionEditPageProps) {
  const { navigate } = useAppRoute()
  const auth = useAuth()
  const establishmentId = auth.activeMembership?.establishment_id ?? null
  const role = auth.activeMembership?.role ?? null
  const membershipId = auth.activeMembership?.id
  const staffMode = role === 'staff'
  const canCrossPole = canDefineCrossPoleTasks(role)
  const detailBackPath = `/action-plans/executions/${executionId}`

  const detailQuery = useActionPlanExecutionDetailQuery(establishmentId, executionId)
  const [form, setForm] = useState<ActionPlanExecutionEditFormValues | null>(null)
  const formRootRef = useRef<HTMLFormElement>(null)
  const lastGuidanceNonceRef = useRef(0)

  // Hydrate once on first load. Realtime refetch must not wipe local edits.
  // Conflict reload rehydrates explicitly via onConflictReload.
  useEffect(() => {
    if (!detailQuery.data || form !== null) {
      return
    }
    startTransition(() => {
      setForm(hydrateActionPlanExecutionEditForm(detailQuery.data))
    })
  }, [detailQuery.data, form])

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
        scopes: auth.activeMembership?.scopes,
        businessUnits,
        filterByScope: role === 'manager' || role === 'staff',
      }),
    [auth.activeMembership?.scopes, businessUnits, role],
  )

  const {
    submit,
    fieldErrors,
    submitError,
    isSubmitting,
    guidanceNonce,
    hasAttemptedSubmit,
    revalidateFrontend,
    clearApiFieldError,
  } = useActionPlanExecutionEditSubmit({
    establishmentId: establishmentId ?? '',
    executionId,
    canDefineCrossPoleTasks: canCrossPole,
    staffMode,
    membershipId,
    onNavigate: navigate,
    onConflictReload: async () => {
      const result = await detailQuery.refetch()
      if (result.data) {
        setForm(hydrateActionPlanExecutionEditForm(result.data))
      }
    },
  })

  const expandAdvancedTaskIds = useMemo(
    () => new Set(taskIdsNeedingAdvancedExpand(fieldErrors)),
    [fieldErrors],
  )

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

  useEffect(() => {
    if (!form || !hasAttemptedSubmit) {
      return
    }
    revalidateFrontend(form)
  }, [form, hasAttemptedSubmit, revalidateFrontend])

  function patchForm(patch: Partial<ActionPlanExecutionEditFormValues>) {
    setForm((previousForm) => {
      if (previousForm === null) {
        return previousForm
      }
      return {
        ...previousForm,
        ...patch,
      }
    })
  }

  if (!establishmentId) {
    return null
  }

  if (detailQuery.isLoading || (!form && !detailQuery.isError)) {
    return (
      <div className="flex items-center justify-center py-16 text-[#7D7B75]">
        <LoaderCircle className="h-6 w-6 animate-spin" />
      </div>
    )
  }

  if (detailQuery.isError || !detailQuery.data || !form) {
    return (
      <TerrainErrorState
        className="mx-3 mt-3"
        message="Ce plan est introuvable ou inaccessible."
        onRetry={() => void detailQuery.refetch()}
      />
    )
  }

  if (!canShowActionPlanExecutionUpdate(detailQuery.data.permission_hints)) {
    return (
      <TerrainErrorState
        className="mx-3 mt-3"
        message="Vous n’avez pas la permission de modifier ce plan."
        onRetry={() => navigate(detailBackPath)}
      />
    )
  }

  if (detailQuery.data.status !== 'in_progress') {
    return (
      <TerrainErrorState
        className="mx-3 mt-3"
        message="Ce plan ne peut plus être modifié dans son état actuel."
        onRetry={() => navigate(detailBackPath)}
      />
    )
  }

  function setPendingTasks(
    update: ActionPlanTaskDraft[] | ((previous: ActionPlanTaskDraft[]) => ActionPlanTaskDraft[]),
  ) {
    setForm((previousForm) => {
      if (previousForm === null) {
        return previousForm
      }
      const pendingTasks =
        typeof update === 'function' ? update(previousForm.pendingTasks) : update
      return {
        ...previousForm,
        pendingTasks,
      }
    })
  }

  function setPlanningDraft(
    update:
      | ActionPlanEventPlanningDraft
      | ((previous: ActionPlanEventPlanningDraft) => ActionPlanEventPlanningDraft),
  ) {
    setForm((previousForm) => {
      if (previousForm === null) {
        return previousForm
      }
      const planningDraft =
        typeof update === 'function' ? update(previousForm.planningDraft) : update
      return {
        ...previousForm,
        planningDraft,
      }
    })
  }

  function handleFormSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    void submit(form)
  }

  return (
    <form
      ref={formRootRef}
      data-testid="action-plan-execution-edit-frame"
      className="flex min-h-full w-full flex-col"
      onSubmit={handleFormSubmit}
    >
      <div className="flex flex-col gap-3 px-3 pb-28 pt-2 lg:gap-4 lg:px-6 lg:pt-4">
        <TerrainCard className="space-y-3">
          <div data-action-plan-field="title">
            <TerrainFieldLabel>Titre</TerrainFieldLabel>
            <Input
              value={form.title}
              onChange={(event) => {
                clearApiFieldError('title')
                patchForm({ title: event.target.value })
              }}
              aria-invalid={fieldErrors.title ? true : undefined}
              className={cn(
                'h-11 border-[#E8E6DF]',
                fieldErrors.title && 'border-destructive',
              )}
            />
            {fieldErrors.title ? (
              <p className="mt-1 text-xs text-destructive">{fieldErrors.title}</p>
            ) : null}
          </div>
          <div>
            <TerrainFieldLabel>Description</TerrainFieldLabel>
            <Textarea
              value={form.description}
              onChange={(event) => patchForm({ description: event.target.value })}
              className="min-h-20 border-[#E8E6DF]"
            />
          </div>
          <PlanningOptionRow
            rowId="pilot-business-unit"
            label="Pôle d'activité pilote"
            value={form.pilotBusinessUnitId}
            displayValue={form.pilotBusinessUnitLabel}
            options={[]}
            disabled
            openPicker={null}
            onOpenPickerChange={() => undefined}
            onChange={() => undefined}
            fieldKey="pilotBusinessUnitId"
          />
        </TerrainCard>

        {!staffMode ? (
          <section className="space-y-2">
            <TerrainSectionLabel>Options</TerrainSectionLabel>
            <TerrainCard className="divide-y divide-[#E8E6DF] p-0">
              <TerrainSwitch
                label="Validation requise"
                checked={form.requiresValidation}
                onCheckedChange={(requiresValidation) => patchForm({ requiresValidation })}
              />
            </TerrainCard>
          </section>
        ) : null}

        {form.treatedTasks.length > 0 ? (
          <section className="space-y-2">
            <TerrainSectionLabel>Tâches traitées</TerrainSectionLabel>
            <div className="space-y-2">
              {form.treatedTasks.map((task) => (
                <ActionPlanTaskReadOnlyRow
                  key={task.id}
                  task={task}
                  statusLabel={formatActionPlanTaskStatusLabel(task.status)}
                />
              ))}
            </div>
          </section>
        ) : null}

        <div>
          <ActionPlanTaskDraftEditor
            tasks={form.pendingTasks}
            establishmentId={establishmentId}
            pilotBusinessUnitId={form.pilotBusinessUnitId}
            canDefineCrossPoleTasks={canCrossPole}
            staffMode={staffMode}
            businessUnits={visibleBusinessUnits}
            fieldErrors={fieldErrors}
            expandAdvancedNonce={guidanceNonce}
            expandAdvancedTaskIds={expandAdvancedTaskIds}
            onTasksChange={setPendingTasks}
            onTaskFieldChange={clearApiFieldError}
          />
        </div>

        <div>
          <ActionPlanEventPlanningForm
            draft={form.planningDraft}
            config={{
              canEditAssignees: !staffMode,
              canSchedule: false,
              staffMode,
              showAdvancedChronology: false,
              lockChronologyMode: true,
              lockStart: true,
              hideAssignees: false,
              staffDisplayName: auth.bootstrap?.user?.username ?? 'Moi',
              assigneeActionsEnabled: false,
            }}
            establishmentId={establishmentId}
            pilotBusinessUnitId={form.pilotBusinessUnitId}
            fieldErrors={fieldErrors}
            onDraftChange={setPlanningDraft}
          />
        </div>

        {submitError ? (
          <div>
            <TerrainFeedback variant="error" message={submitError} />
          </div>
        ) : null}
      </div>

      <TerrainStickyFooter className="lg:px-6">
        <div className="flex gap-2">
          <Button
            type="button"
            variant="outline"
            className="h-11 flex-1 rounded-xl"
            disabled={isSubmitting}
            onClick={() => navigate(detailBackPath)}
          >
            Retour
          </Button>
          <Button
            type="submit"
            className={cn(
              'h-11 flex-1 rounded-xl text-white',
              terrainBrandAction.bg,
              terrainBrandAction.hover,
            )}
            disabled={isSubmitting}
          >
            Enregistrer les modifications
          </Button>
        </div>
      </TerrainStickyFooter>
    </form>
  )
}
