import { useMemo, useState } from 'react'

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
import { useBusinessUnitTreeQuery } from '@/features/auth/hooks'
import { ChecklistFeedback } from '@/features/checklists/components/checklist-feedback'
import { terrain } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

import { ActionPlanAssigneeChronologySheet } from '../components/action-plan-assignee-chronology-sheet'
import {
  ActionPlanTaskDraftEditor,
} from '../components/action-plan-task-draft-editor'
import { useActionPlanCreateSubmit } from '../hooks/use-action-plan-create-submit'
import {
  canCreateActionPlanCatalogEntry,
  canDefineCrossPoleTasks,
} from '../lib/action-plan-management-access'
import {
  createActionPlanTaskDraft,
  type ActionPlanAssigneeDraft,
  type ActionPlanCreateFormValues,
} from '../lib/action-plan-form-validation'

type ActionPlanCreatePageProps = {
  backPath?: string
}

export function ActionPlanCreatePage({ backPath = '/action-plans' }: ActionPlanCreatePageProps) {
  const { navigate } = useAppRoute()
  const { activeMembership } = useAuth()
  const establishmentId = activeMembership?.establishment_id ?? null
  const role = activeMembership?.role ?? null

  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [pilotBusinessUnitId, setPilotBusinessUnitId] = useState('')
  const [requiresValidation, setRequiresValidation] = useState(true)
  const [saveToLibrary, setSaveToLibrary] = useState(false)
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
  const canCreate = canCreateActionPlanCatalogEntry(role)
  const canCrossPole = canDefineCrossPoleTasks(role)

  const resolvedPilotBusinessUnitId =
    pilotBusinessUnitId || businessUnits[0]?.id || ''

  const resolvedTasks = useMemo(() => {
    if (canCrossPole) {
      return tasks
    }
    if (!resolvedPilotBusinessUnitId) {
      return tasks
    }
    return tasks.map((task) => ({
      ...task,
      businessUnitId: task.businessUnitId || resolvedPilotBusinessUnitId,
    }))
  }, [canCrossPole, resolvedPilotBusinessUnitId, tasks])

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
      assignees,
    }),
    [
      assignees,
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
    ],
  )

  const { submit, fieldErrors, submitError, isSubmitting } = useActionPlanCreateSubmit({
    establishmentId: establishmentId ?? '',
    canDefineCrossPoleTasks: canCrossPole,
    onNavigate: navigate,
  })

  if (!establishmentId) {
    return null
  }

  if (!canCreate) {
    return (
      <TerrainErrorState
        className="mx-3 mt-3"
        message="Vous n’avez pas accès à la création de plans d’action."
        onRetry={() => navigate(backPath)}
      />
    )
  }

  return (
    <div className="flex min-h-full flex-col">
      <div className="space-y-3 px-3 pb-28 pt-2">
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
              {businessUnits.map((unit) => (
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
          businessUnits={businessUnits}
          onTasksChange={setTasks}
        />
        {fieldErrors.tasks ? (
          <p className="text-xs text-destructive">{fieldErrors.tasks}</p>
        ) : null}

        {!saveToLibrary ? (
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

        <TerrainCard className="space-y-3">
          <label className="flex items-center justify-between gap-3 text-sm text-[#1a1a1a]">
            <span>Validation requise</span>
            <input
              type="checkbox"
              checked={requiresValidation}
              onChange={(event) => setRequiresValidation(event.target.checked)}
            />
          </label>
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
        </TerrainCard>

        {submitError ? <ChecklistFeedback variant="error" message={submitError} /> : null}
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
    </div>
  )
}
