import { Plus, Trash2 } from 'lucide-react'

import { TerrainCard, TerrainSectionLabel } from '@/components/ui/terrain'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'

import type { ActionPlanTaskDraft } from '../lib/action-plan-form-validation'

type ActionPlanTaskDraftEditorProps = {
  tasks: ActionPlanTaskDraft[]
  pilotBusinessUnitId: string
  canDefineCrossPoleTasks: boolean
  businessUnits: Array<{ id: string; label: string }>
  onTasksChange: (tasks: ActionPlanTaskDraft[]) => void
}

export function createActionPlanTaskDraftEditorItem(
  businessUnitId = '',
): ActionPlanTaskDraft {
  return { id: crypto.randomUUID(), task: '', businessUnitId }
}

export function ActionPlanTaskDraftEditor({
  tasks,
  pilotBusinessUnitId,
  canDefineCrossPoleTasks,
  businessUnits,
  onTasksChange,
}: ActionPlanTaskDraftEditorProps) {
  return (
    <section className="space-y-2">
      <TerrainSectionLabel>Tâches</TerrainSectionLabel>
      <div className="space-y-2">
        {tasks.map((task) => (
          <TerrainCard key={task.id} className="space-y-2 p-3">
            <Input
              value={task.task}
              onChange={(event) =>
                onTasksChange(
                  tasks.map((candidate) =>
                    candidate.id === task.id
                      ? { ...candidate, task: event.target.value }
                      : candidate,
                  ),
                )
              }
              placeholder="Ex. Contrôler la température"
              aria-label="Tâche"
              className="h-10 border-[#E8E6DF] text-sm"
            />
            {canDefineCrossPoleTasks ? (
              <select
                value={task.businessUnitId || pilotBusinessUnitId}
                onChange={(event) =>
                  onTasksChange(
                    tasks.map((candidate) =>
                      candidate.id === task.id
                        ? { ...candidate, businessUnitId: event.target.value }
                        : candidate,
                    ),
                  )
                }
                className="h-10 w-full rounded-xl border border-[#E8E6DF] px-3 text-sm"
                aria-label="Pôle d’activité de la tâche"
              >
                {businessUnits.map((unit) => (
                  <option key={unit.id} value={unit.id}>
                    {unit.label}
                  </option>
                ))}
              </select>
            ) : null}
            <button
              type="button"
              className="rounded-lg p-2 text-[#E24B4A] disabled:opacity-40"
              aria-label="Supprimer la tâche"
              disabled={tasks.length === 1}
              onClick={() => onTasksChange(tasks.filter((candidate) => candidate.id !== task.id))}
            >
              <Trash2 className="h-4 w-4" />
            </button>
          </TerrainCard>
        ))}
        <Button
          type="button"
          variant="outline"
          className={cn(
            'h-11 w-full rounded-xl border-dashed border-[#C8C6BF] bg-white text-[#1B4FD8]',
          )}
          disabled={tasks.length >= 10}
          onClick={() =>
            onTasksChange([
              ...tasks,
              createActionPlanTaskDraftEditorItem(
                canDefineCrossPoleTasks ? pilotBusinessUnitId : pilotBusinessUnitId,
              ),
            ])
          }
        >
          <Plus className="mr-2 h-4 w-4" aria-hidden />
          Ajouter une tâche
        </Button>
      </div>
    </section>
  )
}
