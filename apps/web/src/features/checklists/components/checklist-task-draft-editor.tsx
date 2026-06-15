import { GripVertical, Plus, Trash2 } from 'lucide-react'

import { TerrainCard, TerrainSectionLabel } from '@/components/ui/terrain'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'

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
      <TerrainSectionLabel>Points à réaliser</TerrainSectionLabel>
      <div className="space-y-2">
        {tasks.map((task) => (
          <TerrainCard key={task.id} className="flex items-center gap-2 p-2.5">
            <span
              aria-hidden
              className="h-5 w-5 shrink-0 rounded border border-[#D8D6CF] bg-white"
            />
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
              placeholder="Ex. Désactiver l’alarme"
              aria-label="Point à réaliser"
              className="h-10 flex-1 border-0 bg-transparent p-0 text-sm shadow-none focus-visible:ring-0"
            />
            <GripVertical
              className="h-4 w-4 shrink-0 text-[#C8C6BF]"
              aria-hidden
            />
            <button
              type="button"
              className="rounded-lg p-2 text-[#E24B4A] disabled:opacity-40"
              aria-label="Supprimer le point"
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
          onClick={() => onTasksChange([...tasks, createChecklistTaskDraft()])}
        >
          <Plus className="mr-2 h-4 w-4" aria-hidden />
          Ajouter un point
        </Button>
      </div>
    </section>
  )
}
