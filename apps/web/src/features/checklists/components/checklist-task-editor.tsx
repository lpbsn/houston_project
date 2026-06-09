import { ArrowDown, ArrowUp, LoaderCircle, Pencil, Plus, Trash2 } from 'lucide-react'
import { useState } from 'react'

import { TerrainCard, TerrainSectionLabel } from '@/components/layout/terrain-card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ChecklistFeedback } from '@/features/checklists/components/checklist-feedback'
import {
  useCreateChecklistTaskMutation,
  useDeleteChecklistTaskMutation,
  useReorderChecklistTasksMutation,
  useUpdateChecklistTaskMutation,
} from '@/features/checklists/hooks'
import { resolveChecklistErrorMessage } from '@/features/checklists/lib/checklist-errors'
import { validateTask } from '@/features/checklists/lib/checklist-form-validation'
import type { ChecklistTaskTemplate, ChecklistType } from '@/features/checklists/types'
import { terrain } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

type ChecklistTaskEditorProps = {
  establishmentId: string
  templateId: string
  checklistType: ChecklistType
  tasks: ChecklistTaskTemplate[]
}

export function ChecklistTaskEditor({
  establishmentId,
  templateId,
  checklistType,
  tasks,
}: ChecklistTaskEditorProps) {
  const createMutation = useCreateChecklistTaskMutation(establishmentId, templateId, checklistType)
  const updateMutation = useUpdateChecklistTaskMutation(establishmentId, templateId, checklistType)
  const deleteMutation = useDeleteChecklistTaskMutation(establishmentId, templateId, checklistType)
  const reorderMutation = useReorderChecklistTasksMutation(
    establishmentId,
    templateId,
    checklistType,
  )

  const [newTask, setNewTask] = useState('')
  const [editingTaskId, setEditingTaskId] = useState<string | null>(null)
  const [editDraft, setEditDraft] = useState('')
  const [feedback, setFeedback] = useState<{ variant: 'error' | 'success'; message: string } | null>(
    null,
  )

  const sortedTasks = [...tasks].sort((a, b) => a.position - b.position)
  const isBusy =
    createMutation.isPending ||
    updateMutation.isPending ||
    deleteMutation.isPending ||
    reorderMutation.isPending

  async function handleCreateTask() {
    const validationError = validateTask(newTask)
    if (validationError) {
      setFeedback({ variant: 'error', message: validationError })
      return
    }

    setFeedback(null)
    try {
      await createMutation.mutateAsync({
        task: newTask.trim(),
      })
      setNewTask('')
      setFeedback({ variant: 'success', message: 'Tâche ajoutée.' })
    } catch (error) {
      setFeedback({
        variant: 'error',
        message: resolveChecklistErrorMessage(error, 'La tâche n’a pas pu être ajoutée.'),
      })
    }
  }

  function startEditing(task: ChecklistTaskTemplate) {
    setEditingTaskId(task.id)
    setEditDraft(task.task)
    setFeedback(null)
  }

  async function handleSaveEdit(taskId: string) {
    const validationError = validateTask(editDraft)
    if (validationError) {
      setFeedback({ variant: 'error', message: validationError })
      return
    }

    setFeedback(null)
    try {
      await updateMutation.mutateAsync({
        taskTemplateId: taskId,
        body: {
          task: editDraft.trim(),
        },
      })
      setEditingTaskId(null)
      setFeedback({ variant: 'success', message: 'Tâche mise à jour.' })
    } catch (error) {
      setFeedback({
        variant: 'error',
        message: resolveChecklistErrorMessage(error, 'La tâche n’a pas pu être mise à jour.'),
      })
    }
  }

  async function handleDelete(taskId: string) {
    setFeedback(null)
    try {
      await deleteMutation.mutateAsync(taskId)
      if (editingTaskId === taskId) {
        setEditingTaskId(null)
      }
      setFeedback({ variant: 'success', message: 'Tâche supprimée.' })
    } catch (error) {
      setFeedback({
        variant: 'error',
        message: resolveChecklistErrorMessage(error, 'La tâche n’a pas pu être supprimée.'),
      })
    }
  }

  async function handleMove(taskId: string, direction: 'up' | 'down') {
    const index = sortedTasks.findIndex((task) => task.id === taskId)
    if (index < 0) {
      return
    }

    const targetIndex = direction === 'up' ? index - 1 : index + 1
    if (targetIndex < 0 || targetIndex >= sortedTasks.length) {
      return
    }

    const reordered = [...sortedTasks]
    const [removed] = reordered.splice(index, 1)
    reordered.splice(targetIndex, 0, removed)

    setFeedback(null)
    try {
      await reorderMutation.mutateAsync({
        ordered_task_template_ids: reordered.map((task) => task.id),
      })
    } catch (error) {
      setFeedback({
        variant: 'error',
        message: resolveChecklistErrorMessage(error, 'L’ordre des tâches n’a pas pu être mis à jour.'),
      })
    }
  }

  return (
    <section className="space-y-2">
      <TerrainSectionLabel>Tâches</TerrainSectionLabel>

      {feedback ? <ChecklistFeedback variant={feedback.variant} message={feedback.message} /> : null}

      {sortedTasks.length === 0 ? (
        <TerrainCard className="py-5 text-center">
          <p className={cn('text-sm', terrain.muted)}>Ajoutez au moins une tâche avant activation.</p>
        </TerrainCard>
      ) : (
        <TerrainCard className="divide-y divide-[#F0EFE9] p-0">
          {sortedTasks.map((task, index) => {
            const isEditing = editingTaskId === task.id

            return (
              <div key={task.id} className="px-4 py-3.5">
                {isEditing ? (
                  <div className="space-y-2">
                    <label className="text-xs font-medium text-[#7D7B75]">Tâche</label>
                    <Input
                      value={editDraft}
                      onChange={(e) => setEditDraft(e.target.value)}
                      placeholder="Ex. Vérifier les sanitaires"
                      className="h-10 border-[#E8E6DF] text-sm"
                    />
                    <div className="flex gap-2">
                      <Button
                        type="button"
                        size="sm"
                        className="rounded-lg bg-[#1B4FD8]"
                        disabled={isBusy}
                        onClick={() => void handleSaveEdit(task.id)}
                      >
                        Enregistrer
                      </Button>
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        className="rounded-lg"
                        onClick={() => setEditingTaskId(null)}
                      >
                        Annuler
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-semibold text-[#1a1a1a]">
                        {index + 1}. {task.task}
                      </p>
                    </div>
                    <div className="flex shrink-0 gap-1">
                      <button
                        type="button"
                        className="rounded-lg p-1.5 text-[#7D7B75] hover:bg-[#F5F4F0]"
                        aria-label="Monter la tâche"
                        disabled={isBusy || index === 0}
                        onClick={() => void handleMove(task.id, 'up')}
                      >
                        <ArrowUp className="h-4 w-4" />
                      </button>
                      <button
                        type="button"
                        className="rounded-lg p-1.5 text-[#7D7B75] hover:bg-[#F5F4F0]"
                        aria-label="Descendre la tâche"
                        disabled={isBusy || index === sortedTasks.length - 1}
                        onClick={() => void handleMove(task.id, 'down')}
                      >
                        <ArrowDown className="h-4 w-4" />
                      </button>
                      <button
                        type="button"
                        className="rounded-lg p-1.5 text-[#7D7B75] hover:bg-[#F5F4F0]"
                        aria-label="Modifier la tâche"
                        disabled={isBusy}
                        onClick={() => startEditing(task)}
                      >
                        <Pencil className="h-4 w-4" />
                      </button>
                      <button
                        type="button"
                        className="rounded-lg p-1.5 text-[#E24B4A] hover:bg-[#FFF5F3]"
                        aria-label="Supprimer la tâche"
                        disabled={isBusy}
                        onClick={() => void handleDelete(task.id)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </TerrainCard>
      )}

      <TerrainCard className="space-y-2">
        <label className="text-xs font-medium text-[#7D7B75]">Tâche</label>
        <Input
          value={newTask}
          onChange={(e) => setNewTask(e.target.value)}
          placeholder="Ex. Vérifier les sanitaires"
          className="h-10 border-[#E8E6DF] text-sm"
        />
        <Button
          type="button"
          variant="outline"
          className="h-10 w-full rounded-xl border-[#E8E6DF]"
          disabled={isBusy}
          onClick={() => void handleCreateTask()}
        >
          {createMutation.isPending ? (
            <LoaderCircle className="mr-2 h-4 w-4 animate-spin" aria-hidden />
          ) : (
            <Plus className="mr-2 h-4 w-4" aria-hidden />
          )}
          Ajouter une tâche
        </Button>
      </TerrainCard>
    </section>
  )
}
