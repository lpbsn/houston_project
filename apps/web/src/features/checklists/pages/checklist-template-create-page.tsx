import { LoaderCircle } from 'lucide-react'
import { useState } from 'react'

import { useAppRoute } from '@/app/app-routes'
import { useAuth } from '@/app/auth-provider'
import { TerrainCard, TerrainSectionLabel } from '@/components/layout/terrain-card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ChecklistBusinessUnitSelect } from '@/features/checklists/components/checklist-business-unit-select'
import { ChecklistFeedback } from '@/features/checklists/components/checklist-feedback'
import {
  ChecklistTaskDraftEditor,
  createChecklistTaskDraft,
} from '@/features/checklists/components/checklist-task-draft-editor'
import { ChecklistsApiError } from '@/features/checklists/api'
import {
  useCreateChecklistTemplateWithTasksMutation,
  useQuickCreatePersonalChecklistMutation,
} from '@/features/checklists/hooks'
import { resolveChecklistErrorMessage } from '@/features/checklists/lib/checklist-errors'
import {
  validatePersonalTemplateCreate,
  validateSharedTemplateCreate,
  validateTask,
} from '@/features/checklists/lib/checklist-form-validation'
import type { ChecklistType } from '@/features/checklists/types'

type ChecklistTemplateCreatePageProps = {
  checklistType: ChecklistType
}

export function ChecklistTemplateCreatePage({ checklistType }: ChecklistTemplateCreatePageProps) {
  const { navigate } = useAppRoute()
  const { activeMembership } = useAuth()
  const establishmentId = activeMembership?.establishment_id ?? null

  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [businessUnitId, setBusinessUnitId] = useState('')
  const [tasks, setTasks] = useState([createChecklistTaskDraft()])
  const [feedback, setFeedback] = useState<{ variant: 'error' | 'success'; message: string } | null>(
    null,
  )
  const [activeExecutionId, setActiveExecutionId] = useState<string | null>(null)

  const sharedCreateMutation = useCreateChecklistTemplateWithTasksMutation(establishmentId ?? '')
  const personalCreateMutation = useQuickCreatePersonalChecklistMutation(establishmentId ?? '')

  if (!establishmentId) {
    return null
  }

  const isShared = checklistType === 'shared'
  const isPending = isShared ? sharedCreateMutation.isPending : personalCreateMutation.isPending

  async function handleSubmit() {
    const validationError = isShared
      ? validateSharedTemplateCreate({ title, businessUnitId })
      : validatePersonalTemplateCreate({ title })

    if (validationError) {
      setFeedback({ variant: 'error', message: validationError })
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

    const taskPayload = normalizedTasks.map((taskValue) => ({ task: taskValue }))

    try {
      if (isShared) {
        await sharedCreateMutation.mutateAsync({
          checklist_type: 'shared',
          title: title.trim(),
          description: description.trim(),
          business_unit_id: businessUnitId,
          tasks: taskPayload,
        })
        navigate('/checklists', { replace: true })
        return
      }

      const execution = await personalCreateMutation.mutateAsync({
        title: title.trim(),
        description: description.trim(),
        tasks: taskPayload,
      })
      navigate(`/checklists/executions/${execution.id}`, { replace: true })
    } catch (error) {
      if (error instanceof ChecklistsApiError && error.activeExecutionId) {
        setActiveExecutionId(error.activeExecutionId)
      }
      setFeedback({
        variant: 'error',
        message: resolveChecklistErrorMessage(error, 'La checklist n’a pas pu être créée.'),
      })
    }
  }

  return (
    <div className="space-y-3 px-3 pb-28 pt-3">
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

      {isShared ? (
        <ChecklistBusinessUnitSelect
          establishmentId={establishmentId}
          selectedBusinessUnitId={businessUnitId}
          onBusinessUnitChange={setBusinessUnitId}
        />
      ) : null}

      <section className="space-y-1.5">
        <TerrainSectionLabel>Titre</TerrainSectionLabel>
        <TerrainCard>
          <Input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder={isShared ? 'Ex. Ouverture cuisine' : 'Ex. Ma routine du matin'}
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
            className="min-h-[88px] w-full resize-y bg-transparent text-[14px] leading-relaxed text-[#444] outline-none placeholder:text-[#aaa]"
          />
        </TerrainCard>
      </section>

      <ChecklistTaskDraftEditor tasks={tasks} onTasksChange={setTasks} />

      <Button
        type="button"
        className="h-11 w-full rounded-xl bg-[#1B4FD8] text-white hover:bg-[#1B4FD8]/95"
        disabled={isPending}
        onClick={() => void handleSubmit()}
      >
        {isPending ? (
          <LoaderCircle className="mr-2 h-4 w-4 animate-spin" aria-hidden />
        ) : null}
        {isShared ? 'Créer la checklist' : 'Créer et démarrer'}
      </Button>
    </div>
  )
}
