import { Plus, Trash2 } from 'lucide-react'

import { TerrainCard, TerrainSectionLabel } from '@/components/layout/terrain-card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

export type ChecklistTaskDraft = {
  id: string
  task: string
}

export function createChecklistTaskDraft(): ChecklistTaskDraft {
  return { id: crypto.randomUUID(), task: '' }
}

type ChecklistTaskDraftEditorProps = {
  tasks: ChecklistTaskDraft[]
  onTasksChange: (tasks: ChecklistTaskDraft[]) => void
}

export function ChecklistTaskDraftEditor({
  tasks,
  onTasksChange,
}: ChecklistTaskDraftEditorProps) {
  return (
    <section className="space-y-2">
      <TerrainSectionLabel>Tâches</TerrainSectionLabel>
      <TerrainCard className="space-y-2">
        {tasks.map((task, index) => (
          <div key={task.id} className="flex items-center gap-2">
            <span className="w-5 shrink-0 text-xs text-[#7D7B75]">{index + 1}.</span>
            <Input
              value={task.task}
              onChange={(e) =>
                onTasksChange(
                  tasks.map((candidate) =>
                    candidate.id === task.id
                      ? { ...candidate, task: e.target.value }
                      : candidate,
                  ),
                )
              }
              placeholder="Ex. Vérifier les sanitaires"
              aria-label="Tâche"
              className="h-10 flex-1 border-[#E8E6DF] text-sm"
            />
            <button
              type="button"
              className="rounded-lg p-2 text-[#E24B4A] disabled:opacity-40"
              aria-label="Supprimer la tâche"
              disabled={tasks.length === 1}
              onClick={() => onTasksChange(tasks.filter((candidate) => candidate.id !== task.id))}
            >
              <Trash2 className="h-4 w-4" />
            </button>
          </div>
        ))}
        <Button
          type="button"
          variant="outline"
          className="h-10 w-full rounded-xl border-[#E8E6DF]"
          onClick={() => onTasksChange([...tasks, createChecklistTaskDraft()])}
        >
          <Plus className="mr-2 h-4 w-4" aria-hidden />
          Ajouter une tâche
        </Button>
      </TerrainCard>
    </section>
  )
}
