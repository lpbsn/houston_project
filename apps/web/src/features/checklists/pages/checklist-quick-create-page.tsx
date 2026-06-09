import { LoaderCircle } from 'lucide-react'
import { useState } from 'react'

import { useAppRoute } from '@/app/app-routes'
import { useAuth } from '@/app/auth-provider'
import { TerrainCard, TerrainSectionLabel } from '@/components/layout/terrain-card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ChecklistFeedback } from '@/features/checklists/components/checklist-feedback'
import {
  ChecklistTaskDraftEditor,
  createChecklistTaskDraft,
} from '@/features/checklists/components/checklist-task-draft-editor'
import { useQuickCreatePersonalChecklistMutation } from '@/features/checklists/hooks'
import { ChecklistsApiError } from '@/features/checklists/api'
import { resolveChecklistErrorMessage } from '@/features/checklists/lib/checklist-errors'
import { validatePersonalTemplateCreate, validateTask } from '@/features/checklists/lib/checklist-form-validation'

export function ChecklistQuickCreatePage() {
  const { navigate } = useAppRoute()
  const { activeMembership } = useAuth()
  const establishmentId = activeMembership?.establishment_id ?? null

  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [tasks, setTasks] = useState([createChecklistTaskDraft()])
  const [feedback, setFeedback] = useState<{ variant: 'error' | 'success'; message: string } | null>(
    null,
  )
  const [activeExecutionId, setActiveExecutionId] = useState<string | null>(null)

  const createMutation = useQuickCreatePersonalChecklistMutation(establishmentId ?? '')

  if (!establishmentId) {
    return null
  }

  async function handleSubmit() {
    const titleError = validatePersonalTemplateCreate({ title })
    if (titleError) {
      setFeedback({ variant: 'error', message: titleError })
      return
    }

    const normalizedTasks = tasks.map((task) => task.task.trim()).filter(Boolean)
    if (normalizedTasks.length === 0) {
      setFeedback({ variant: 'error', message: 'Ajoutez au moins une tâche.' })
      return
    }

    for (const taskValue of normalizedTasks) {
      const taskError = validateTask(taskValue)
      if (taskError) {
        setFeedback({ variant: 'error', message: taskError })
        return
      }
    }

    setFeedback(null)
    setActiveExecutionId(null)

    try {
      const execution = await createMutation.mutateAsync({
        title: title.trim(),
        description: description.trim(),
        tasks: normalizedTasks.map((taskValue) => ({ task: taskValue })),
      })
      navigate(`/checklists/executions/${execution.id}`, { replace: true })
    } catch (error) {
      if (error instanceof ChecklistsApiError && error.activeExecutionId) {
        setActiveExecutionId(error.activeExecutionId)
      }
      setFeedback({
        variant: 'error',
        message: resolveChecklistErrorMessage(
          error,
          'La checklist personnelle n’a pas pu être créée.',
        ),
      })
    }
  }

  return (
    <div className="space-y-3 px-3 pb-28 pt-3">
      <p className="text-sm leading-6 text-[#7D7B75]">
        Créez une checklist personnelle et démarrez son exécution immédiatement.
      </p>

      {feedback ? <ChecklistFeedback variant={feedback.variant} message={feedback.message} /> : null}

      {activeExecutionId ? (
        <Button
          type="button"
          variant="outline"
          className="h-10 w-full rounded-xl border-[#E8E6DF]"
          onClick={() => navigate(`/checklists/executions/${activeExecutionId}`)}
        >
          Ouvrir l&apos;exécution en cours
        </Button>
      ) : null}

      <section className="space-y-1.5">
        <TerrainSectionLabel>Titre</TerrainSectionLabel>
        <TerrainCard>
          <Input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Ex. Ma routine du matin"
            className="border-0 bg-transparent p-0 text-[15px] shadow-none focus-visible:ring-0"
          />
        </TerrainCard>
      </section>

      <section className="space-y-1.5">
        <TerrainSectionLabel>Description</TerrainSectionLabel>
        <TerrainCard>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Description optionnelle"
            className="min-h-[72px] w-full resize-y bg-transparent text-[14px] leading-relaxed text-[#444] outline-none placeholder:text-[#aaa]"
          />
        </TerrainCard>
      </section>

      <ChecklistTaskDraftEditor tasks={tasks} onTasksChange={setTasks} />

      <Button
        type="button"
        className="h-11 w-full rounded-xl bg-[#1B4FD8] text-white hover:bg-[#1B4FD8]/95"
        disabled={createMutation.isPending}
        onClick={() => void handleSubmit()}
      >
        {createMutation.isPending ? (
          <LoaderCircle className="mr-2 h-4 w-4 animate-spin" aria-hidden />
        ) : null}
        Créer et démarrer
      </Button>
    </div>
  )
}
