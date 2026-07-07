import { ChevronRight, Plus, Trash2 } from 'lucide-react'
import { useState } from 'react'

import { TerrainCard, TerrainSectionLabel } from '@/components/ui/terrain'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'

import {
  combineDateAndTimeToIso,
  splitIsoToDateAndTime,
} from '../lib/action-plan-event-planning-form'
import { formatActionPlanTaskEditorMetaLine } from '../lib/action-plan-display'
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
  onTasksChange: (tasks: ActionPlanTaskDraft[]) => void
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

type ActionPlanTaskDraftCardProps = {
  task: ActionPlanTaskDraft
  establishmentId: string
  pilotBusinessUnitId: string
  canDefineCrossPoleTasks: boolean
  staffMode: boolean
  businessUnits: Array<{ id: string; label: string }>
  canDelete: boolean
  onChange: (task: ActionPlanTaskDraft) => void
  onDelete: () => void
}

function ActionPlanTaskDraftCard({
  task,
  establishmentId,
  pilotBusinessUnitId,
  staffMode,
  businessUnits,
  canDelete,
  onChange,
  onDelete,
}: ActionPlanTaskDraftCardProps) {
  const [advancedExpanded, setAdvancedExpanded] = useState(false)
  const [openPicker, setOpenPicker] = useState<PlanningPickerTarget>(null)
  const [openPolePicker, setOpenPolePicker] = useState<PlanningOptionPickerTarget>(null)
  const [assigneeSheetOpen, setAssigneeSheetOpen] = useState(false)
  const poleAssigneeState = resolveTaskPoleAssigneeState({
    task,
    pilotBusinessUnitId,
    businessUnits,
  })

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

  function updateDeadline(date: string, time: string) {
    onChange({
      ...task,
      deadlineAt: combineDateAndTimeToIso(date, time),
    })
  }

  function handleBusinessUnitChange(businessUnitId: string) {
    const clearAssignee = shouldClearAssigneeOnPoleChange(task, businessUnitId)
    onChange({
      ...task,
      businessUnitId,
      ...(clearAssignee
        ? { assigneeMembershipId: '', assigneeDisplayName: '', assigneeBusinessUnitIds: [] }
        : {}),
    })
  }

  function handleAssigneeChange(
    membershipId: string,
    user: { display_name: string; business_unit_ids?: string[] },
  ) {
    onChange(
      applyAssigneeSelectionToTask(task, {
        membershipId,
        displayName: user.display_name,
        businessUnitIds: user.business_unit_ids ?? [],
      }),
    )
  }

  function handleClearAssignee() {
    onChange({
      ...task,
      assigneeMembershipId: '',
      assigneeDisplayName: '',
      assigneeBusinessUnitIds: [],
      businessUnitId: '',
    })
  }

  return (
    <TerrainCard className="space-y-2 p-3">
      <div className="flex items-start gap-2">
        <div className="min-w-0 flex-1 space-y-2">
          <div className="flex items-start justify-between gap-2">
            <Input
              value={task.task}
              onChange={(event) => onChange({ ...task, task: event.target.value })}
              placeholder="Ex. Contrôler la température"
              aria-label="Titre de la tâche"
              className="h-10 border-[#E8E6DF] text-sm"
            />
            {metaLine ? (
              <p className="max-w-[45%] shrink-0 pt-2.5 text-right text-xs text-[#7D7B75]">
                {metaLine}
              </p>
            ) : null}
          </div>
          <textarea
            value={task.description}
            onChange={(event) => onChange({ ...task, description: event.target.value })}
            placeholder="Description (optionnelle)"
            aria-label="Description de la tâche"
            className="min-h-16 w-full rounded-xl border border-[#E8E6DF] px-3 py-2 text-sm"
          />
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
          <PlanningDateTimeRow
            rowId={`task-${task.id}-deadline`}
            label="Deadline"
            date={deadlineDate}
            time={deadlineTime}
            openPicker={openPicker}
            onOpenPickerChange={setOpenPicker}
            onDateChange={(date) => updateDeadline(date, deadlineTime)}
            onTimeChange={(time) => updateDeadline(deadlineDate, time)}
          />
          {!staffMode ? (
            <div className="border-b border-[#E8E6DF] px-3 py-3">
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
            </div>
          ) : null}
          <div className="px-3 py-3">
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
            />
            {poleAssigneeState.requiresPoleChoice ? (
              <p className="mt-1 text-xs text-[#7D7B75]">
                {task.assigneeMembershipId && task.assigneeBusinessUnitIds.length === 0
                  ? "Choisissez un pôle d'activité pour cette tâche."
                  : 'Choisissez le pôle de l’assigné.'}
              </p>
            ) : null}
            {!task.businessUnitId && !task.assigneeMembershipId ? (
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
  onTasksChange,
}: ActionPlanTaskDraftEditorProps) {
  return (
    <section className="space-y-2">
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
            onChange={(nextTask) =>
              onTasksChange(
                tasks.map((candidate) => (candidate.id === task.id ? nextTask : candidate)),
              )
            }
            onDelete={() => onTasksChange(tasks.filter((candidate) => candidate.id !== task.id))}
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
            onTasksChange([...tasks, createActionPlanTaskDraftEditorItem()])
          }
        >
          <Plus className="mr-2 h-4 w-4" aria-hidden />
          Ajouter une tâche
        </Button>
      </div>
    </section>
  )
}
