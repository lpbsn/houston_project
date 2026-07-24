import { ChevronRight, Plus, Trash2 } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'

import { TerrainCard, TerrainSectionLabel } from '@/components/ui/terrain'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { cn } from '@/lib/utils'

import {
  combineDateAndTimeToIso,
  splitIsoToDateAndTime,
} from '../lib/action-plan-event-planning-form'
import { formatActionPlanTaskEditorMetaLine } from '../lib/action-plan-display'
import {
  ACTION_PLAN_FIELD_ATTR,
} from '../lib/action-plan-form-guidance'
import { actionPlanTaskFieldKey } from '../lib/action-plan-field-errors'
import type { ActionPlanTaskDraft } from '../lib/action-plan-form-validation'
import {
  applyAssigneeSelectionToTask,
  isAdminAssigneeTask,
  resolveTaskPoleAssigneeState,
  shouldClearAssigneeOnPoleChange,
} from '../lib/resolve-task-pole-assignee-state'
import { ActionPlanTaskAssigneeSheet } from './action-plan-task-assignee-sheet'
import {
  PlanningDateTimeRow,
  type PlanningPickerTarget,
} from './planning/planning-date-time-row'
import {
  PlanningOptionRow,
  type PlanningOptionPickerTarget,
} from './planning/planning-option-row'

type ActionPlanTaskDraftEditorProps = {
  tasks: ActionPlanTaskDraft[]
  establishmentId: string
  pilotBusinessUnitId: string
  canDefineCrossPoleTasks: boolean
  staffMode?: boolean
  businessUnits: Array<{ id: string; label: string }>
  fieldErrors?: Record<string, string>
  /** One-shot expand request for advanced options (nonce increments per invalid submit). */
  expandAdvancedNonce?: number
  expandAdvancedTaskIds?: ReadonlySet<string> | readonly string[]
  onTasksChange: (
    update: ActionPlanTaskDraft[] | ((previous: ActionPlanTaskDraft[]) => ActionPlanTaskDraft[]),
  ) => void
  onTaskFieldChange?: (fieldKey: string) => void
}

export function createActionPlanTaskDraftEditorItem(
  businessUnitId = '',
): ActionPlanTaskDraft {
  return {
    id: crypto.randomUUID(),
    task: '',
    description: '',
    businessUnitId,
    deadlineAt: '',
    assigneeMembershipId: '',
    assigneeDisplayName: '',
    assigneeBusinessUnitIds: [],
  }
}

type TaskPatch =
  | Partial<ActionPlanTaskDraft>
  | ((previousTask: ActionPlanTaskDraft) => Partial<ActionPlanTaskDraft>)

type ActionPlanTaskDraftCardProps = {
  task: ActionPlanTaskDraft
  establishmentId: string
  pilotBusinessUnitId: string
  canDefineCrossPoleTasks: boolean
  staffMode: boolean
  businessUnits: Array<{ id: string; label: string }>
  canDelete: boolean
  fieldErrors: Record<string, string>
  expandAdvancedNonce: number
  shouldExpandAdvanced: boolean
  onChange: (patch: TaskPatch) => void
  onDelete: () => void
  onTaskFieldChange?: (fieldKey: string) => void
}

function ActionPlanTaskDraftCard({
  task,
  establishmentId,
  pilotBusinessUnitId,
  staffMode,
  businessUnits,
  canDelete,
  fieldErrors,
  expandAdvancedNonce,
  shouldExpandAdvanced,
  onChange,
  onDelete,
  onTaskFieldChange,
}: ActionPlanTaskDraftCardProps) {
  const [advancedExpanded, setAdvancedExpanded] = useState(false)
  const lastExpandNonceRef = useRef(0)
  const [openPicker, setOpenPicker] = useState<PlanningPickerTarget>(null)
  const [openPolePicker, setOpenPolePicker] = useState<PlanningOptionPickerTarget>(null)
  const [assigneeSheetOpen, setAssigneeSheetOpen] = useState(false)
  const poleAssigneeState = resolveTaskPoleAssigneeState({
    task,
    pilotBusinessUnitId,
    businessUnits,
  })

  useEffect(() => {
    if (
      expandAdvancedNonce > lastExpandNonceRef.current &&
      shouldExpandAdvanced
    ) {
      lastExpandNonceRef.current = expandAdvancedNonce
      setAdvancedExpanded(true)
    }
  }, [expandAdvancedNonce, shouldExpandAdvanced])

  const taskBusinessUnitOptions = poleAssigneeState.poleOptions.map((unit) => ({
    value: unit.id,
    label: unit.label,
  }))
  const taskPoleDisplayValue = task.businessUnitId
    ? taskBusinessUnitOptions.find((option) => option.value === task.businessUnitId)?.label
    : !task.assigneeMembershipId
      ? taskBusinessUnitOptions.find(
          (option) => option.value === poleAssigneeState.effectiveBusinessUnitId,
        )?.label
      : undefined
  const { date: deadlineDate, time: deadlineTime } = splitIsoToDateAndTime(task.deadlineAt)
  const metaLine = formatActionPlanTaskEditorMetaLine({
    assigneeDisplayName: task.assigneeDisplayName || null,
    deadlineAt: task.deadlineAt || null,
  })

  const titleKey = actionPlanTaskFieldKey(task.id, 'task')
  const descriptionKey = actionPlanTaskFieldKey(task.id, 'description')
  const deadlineKey = actionPlanTaskFieldKey(task.id, 'deadlineAt')
  const assigneeKey = actionPlanTaskFieldKey(task.id, 'assignee')
  const poleKey = actionPlanTaskFieldKey(task.id, 'businessUnitId')
  const titleError = fieldErrors[titleKey]
  const descriptionError = fieldErrors[descriptionKey]
  const deadlineError = fieldErrors[deadlineKey]
  const assigneeError = fieldErrors[assigneeKey]
  const poleError = fieldErrors[poleKey]
  const hasTaskError = Boolean(
    titleError || descriptionError || deadlineError || assigneeError || poleError,
  )

  function updateDeadline(date: string, time: string) {
    onTaskFieldChange?.(deadlineKey)
    onChange({
      deadlineAt: combineDateAndTimeToIso(date, time),
    })
  }

  function handleBusinessUnitChange(businessUnitId: string) {
    onTaskFieldChange?.(poleKey)
    onChange((previousTask) => {
      const clearAssignee = shouldClearAssigneeOnPoleChange(previousTask, businessUnitId)
      return {
        businessUnitId,
        ...(clearAssignee
          ? { assigneeMembershipId: '', assigneeDisplayName: '', assigneeBusinessUnitIds: [] }
          : {}),
      }
    })
  }

  function handleAssigneeChange(
    membershipId: string,
    user: { display_name: string; business_unit_ids?: string[] },
  ) {
    onTaskFieldChange?.(assigneeKey)
    onChange((previousTask) => {
      const nextTask = applyAssigneeSelectionToTask(previousTask, {
        membershipId,
        displayName: user.display_name,
        businessUnitIds: user.business_unit_ids ?? [],
      })
      return {
        assigneeMembershipId: nextTask.assigneeMembershipId,
        assigneeDisplayName: nextTask.assigneeDisplayName,
        assigneeBusinessUnitIds: nextTask.assigneeBusinessUnitIds,
        businessUnitId: nextTask.businessUnitId,
      }
    })
  }

  function handleClearAssignee() {
    onTaskFieldChange?.(assigneeKey)
    onChange({
      assigneeMembershipId: '',
      assigneeDisplayName: '',
      assigneeBusinessUnitIds: [],
      businessUnitId: '',
    })
  }

  return (
    <TerrainCard
      className={cn(
        'space-y-2 p-3',
        hasTaskError && 'border-destructive/60 ring-1 ring-destructive/30',
      )}
    >
      <div className="flex items-start gap-2">
        <div className="min-w-0 flex-1 space-y-2">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0 flex-1" {...{ [ACTION_PLAN_FIELD_ATTR]: titleKey }}>
              <Input
                value={task.task}
                onChange={(event) => {
                  onTaskFieldChange?.(titleKey)
                  onChange({ task: event.target.value })
                }}
                placeholder="Ex. Contrôler la température"
                aria-label="Titre de la tâche"
                aria-invalid={titleError ? true : undefined}
                className={cn(
                  'h-10 border-[#E8E6DF]',
                  titleError && 'border-destructive',
                )}
              />
              {titleError ? (
                <p className="mt-1 text-xs text-destructive">{titleError}</p>
              ) : null}
            </div>
            {metaLine ? (
              <p className="max-w-[45%] shrink-0 pt-2.5 text-right text-xs text-[#7D7B75]">
                {metaLine}
              </p>
            ) : null}
          </div>
          <div {...{ [ACTION_PLAN_FIELD_ATTR]: descriptionKey }}>
            <Textarea
              value={task.description}
              onChange={(event) => {
                onTaskFieldChange?.(descriptionKey)
                onChange({ description: event.target.value })
              }}
              placeholder="Description (optionnelle)"
              aria-label="Description de la tâche"
              aria-invalid={descriptionError ? true : undefined}
              className={cn(
                'min-h-16 border-[#E8E6DF]',
                descriptionError && 'border-destructive',
              )}
            />
            {descriptionError ? (
              <p className="mt-1 text-xs text-destructive">{descriptionError}</p>
            ) : null}
          </div>
        </div>
        <button
          type="button"
          className="rounded-lg p-2 text-[#E24B4A] disabled:opacity-40"
          aria-label="Supprimer la tâche"
          disabled={!canDelete}
          onClick={onDelete}
        >
          <Trash2 className="h-4 w-4" />
        </button>
      </div>

      <button
        type="button"
        className="flex w-full items-center gap-2 text-left text-sm text-[#1B4FD8]"
        aria-expanded={advancedExpanded}
        onClick={() => setAdvancedExpanded((value) => !value)}
      >
        <ChevronRight
          className={cn('h-4 w-4 transition-transform', advancedExpanded && 'rotate-90')}
          aria-hidden
        />
        Options avancées
      </button>

      {advancedExpanded ? (
        <TerrainCard className="overflow-hidden p-0">
          <div {...{ [ACTION_PLAN_FIELD_ATTR]: deadlineKey }}>
            <PlanningDateTimeRow
              rowId={`task-${task.id}-deadline`}
              label="Deadline"
              date={deadlineDate}
              time={deadlineTime}
              openPicker={openPicker}
              onOpenPickerChange={setOpenPicker}
              onDateChange={(date) => updateDeadline(date, deadlineTime)}
              onTimeChange={(time) => updateDeadline(deadlineDate, time)}
              error={deadlineError}
            />
          </div>
          {!staffMode ? (
            <div
              className="border-b border-[#E8E6DF] px-3 py-3"
              {...{ [ACTION_PLAN_FIELD_ATTR]: assigneeKey }}
            >
              <div className="flex items-center justify-between gap-3">
                <span className="text-sm text-[#1a1a1a]">Assigné</span>
                <div className="flex items-center gap-2">
                  {task.assigneeMembershipId ? (
                    <Button
                      type="button"
                      variant="ghost"
                      className="h-9 rounded-xl px-2 text-xs text-[#7D7B75]"
                      onClick={handleClearAssignee}
                    >
                      Effacer
                    </Button>
                  ) : null}
                  <Button
                    type="button"
                    variant="outline"
                    className="h-9 rounded-xl text-xs"
                    disabled={!poleAssigneeState.canPickAssignee}
                    onClick={() => setAssigneeSheetOpen(true)}
                  >
                    {task.assigneeDisplayName || 'Choisir'}
                  </Button>
                </div>
              </div>
              {assigneeError ? (
                <p className="mt-1 text-xs text-destructive">{assigneeError}</p>
              ) : null}
            </div>
          ) : null}
          <div className="px-3 py-3" {...{ [ACTION_PLAN_FIELD_ATTR]: poleKey }}>
            <PlanningOptionRow
              rowId={`task-${task.id}-pole`}
              label="Pôle d'activité"
              value={task.businessUnitId}
              displayValue={taskPoleDisplayValue}
              options={taskBusinessUnitOptions}
              openPicker={openPolePicker}
              onOpenPickerChange={setOpenPolePicker}
              onChange={handleBusinessUnitChange}
              disabled={poleAssigneeState.poleLocked}
              error={poleError}
            />
            {poleAssigneeState.requiresPoleChoice && !poleError ? (
              <p className="mt-1 text-xs text-[#7D7B75]">
                {task.assigneeMembershipId && task.assigneeBusinessUnitIds.length === 0
                  ? "Choisissez un pôle d'activité pour cette tâche."
                  : 'Choisissez le pôle de l’assigné.'}
              </p>
            ) : null}
            {!task.businessUnitId && !task.assigneeMembershipId && !poleError ? (
              <p className="mt-1 text-xs text-[#7D7B75]">
                Sans pôle explicite, le pôle pilote sera utilisé.
              </p>
            ) : null}
          </div>
        </TerrainCard>
      ) : null}

      <ActionPlanTaskAssigneeSheet
        open={assigneeSheetOpen && poleAssigneeState.canPickAssignee}
        establishmentId={establishmentId}
        businessUnitId={
          task.businessUnitId ||
          (isAdminAssigneeTask(task) ? undefined : poleAssigneeState.effectiveBusinessUnitId) ||
          undefined
        }
        assigneeMembershipId={task.assigneeMembershipId}
        assigneeDisplayName={task.assigneeDisplayName}
        onAssigneeChange={handleAssigneeChange}
        onClose={() => setAssigneeSheetOpen(false)}
        onConfirm={() => setAssigneeSheetOpen(false)}
      />
    </TerrainCard>
  )
}

export function ActionPlanTaskDraftEditor({
  tasks,
  establishmentId,
  pilotBusinessUnitId,
  canDefineCrossPoleTasks,
  staffMode = false,
  businessUnits,
  fieldErrors = {},
  expandAdvancedNonce = 0,
  expandAdvancedTaskIds,
  onTasksChange,
  onTaskFieldChange,
}: ActionPlanTaskDraftEditorProps) {
  const expandIds =
    expandAdvancedTaskIds instanceof Set
      ? expandAdvancedTaskIds
      : new Set(expandAdvancedTaskIds ?? [])

  return (
    <section className="space-y-2" {...{ [ACTION_PLAN_FIELD_ATTR]: 'tasks' }}>
      <TerrainSectionLabel>Tâches</TerrainSectionLabel>
      <div className="space-y-2">
        {tasks.map((task) => (
          <ActionPlanTaskDraftCard
            key={task.id}
            task={task}
            establishmentId={establishmentId}
            pilotBusinessUnitId={pilotBusinessUnitId}
            canDefineCrossPoleTasks={canDefineCrossPoleTasks}
            staffMode={staffMode}
            businessUnits={businessUnits}
            canDelete
            fieldErrors={fieldErrors}
            expandAdvancedNonce={expandAdvancedNonce}
            shouldExpandAdvanced={expandIds.has(task.id)}
            onChange={(patch) =>
              onTasksChange((previousTasks) =>
                previousTasks.map((previousTask) => {
                  if (previousTask.id !== task.id) {
                    return previousTask
                  }
                  const resolvedPatch =
                    typeof patch === 'function' ? patch(previousTask) : patch
                  return { ...previousTask, ...resolvedPatch }
                }),
              )
            }
            onDelete={() =>
              onTasksChange((previousTasks) =>
                previousTasks.filter((candidate) => candidate.id !== task.id),
              )
            }
            onTaskFieldChange={onTaskFieldChange}
          />
        ))}
        <Button
          type="button"
          variant="outline"
          className={cn(
            'h-11 w-full rounded-xl border-dashed border-[#C8C6BF] bg-white text-[#1B4FD8]',
          )}
          disabled={tasks.length >= 10}
          onClick={() =>
            onTasksChange((previousTasks) => [
              ...previousTasks,
              createActionPlanTaskDraftEditorItem(),
            ])
          }
        >
          <Plus className="mr-2 h-4 w-4" aria-hidden />
          Ajouter une tâche
        </Button>
      </div>
      {fieldErrors.tasks ? (
        <p className="text-xs text-destructive">{fieldErrors.tasks}</p>
      ) : null}
    </section>
  )
}
