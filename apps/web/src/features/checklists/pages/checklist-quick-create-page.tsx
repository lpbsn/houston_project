import { LoaderCircle } from 'lucide-react'
import { useState } from 'react'

import { useAppRoute } from '@/app/app-routes'
import { useAuth } from '@/app/auth-provider'
import { TerrainCard, TerrainSectionLabel } from '@/components/layout/terrain-card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ActionCreateAssigneeSection } from '@/features/actions/components/action-create-assignee-section'
import { ActionCreateDeadlineSection } from '@/features/actions/components/action-create-deadline-section'
import {
  applyDeadlinePreset,
  buildDueAtFromParts,
  syncDeadlineFieldsFromDueAt,
  type DeadlinePreset,
} from '@/features/actions/lib/action-create-deadline'
import type { ScopedUserSearchResult } from '@/features/actions/types'
import { ChecklistBusinessUnitSelect } from '@/features/checklists/components/checklist-business-unit-select'
import { ChecklistFeedback } from '@/features/checklists/components/checklist-feedback'
import {
  ChecklistTaskDraftEditor,
  createChecklistTaskDraft,
} from '@/features/checklists/components/checklist-task-draft-editor'
import { useCreateFlashTodoMutation } from '@/features/checklists/hooks'
import { resolveChecklistErrorMessage } from '@/features/checklists/lib/checklist-errors'
import { validateFlashTodoCreate, validateTask } from '@/features/checklists/lib/checklist-form-validation'

export function ChecklistQuickCreatePage() {
  const { navigate } = useAppRoute()
  const { activeMembership } = useAuth()
  const establishmentId = activeMembership?.establishment_id ?? null

  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [businessUnitId, setBusinessUnitId] = useState('')
  const [assignedTo, setAssignedTo] = useState(activeMembership?.id ?? '')
  const [selectedUser, setSelectedUser] = useState<ScopedUserSearchResult | null>(null)
  const [tasks, setTasks] = useState([createChecklistTaskDraft()])
  const [hasDeadline, setHasDeadline] = useState(false)
  const [selectedPreset, setSelectedPreset] = useState<DeadlinePreset | null>('2h')
  const [limitDate, setLimitDate] = useState('')
  const [limitHours, setLimitHours] = useState('')
  const [limitMinutes, setLimitMinutes] = useState('')
  const [feedback, setFeedback] = useState<{ variant: 'error' | 'success'; message: string } | null>(
    null,
  )

  const createMutation = useCreateFlashTodoMutation(establishmentId ?? '')

  if (!establishmentId) {
    return null
  }

  function enableDeadline() {
    const initialDue = applyDeadlinePreset('2h', new Date())
    const synced = syncDeadlineFieldsFromDueAt(initialDue)
    setHasDeadline(true)
    setSelectedPreset('2h')
    setLimitDate(synced.limitDate)
    setLimitHours(synced.limitHours)
    setLimitMinutes(synced.limitMinutes)
  }

  function applyDueAtFromFields(dateStr: string, hoursStr: string, minutesStr: string): Date | null {
    const hours = Number.parseInt(hoursStr, 10)
    const minutes = Number.parseInt(minutesStr, 10)
    if (Number.isNaN(hours) || Number.isNaN(minutes) || !dateStr) {
      return null
    }
    return buildDueAtFromParts(dateStr, hours, minutes)
  }

  function handlePresetChange(preset: DeadlinePreset) {
    const next = applyDeadlinePreset(preset, new Date())
    const synced = syncDeadlineFieldsFromDueAt(next)
    setSelectedPreset(preset)
    setLimitDate(synced.limitDate)
    setLimitHours(synced.limitHours)
    setLimitMinutes(synced.limitMinutes)
  }

  function handleLimitDateChange(value: string) {
    setLimitDate(value)
    setSelectedPreset(null)
  }

  function handleLimitTimeChange(hours: string, minutes: string) {
    setLimitHours(hours)
    setLimitMinutes(minutes)
    setSelectedPreset(null)
  }

  function handleAssigneeChange(membershipId: string, user: ScopedUserSearchResult) {
    setAssignedTo(membershipId)
    setSelectedUser(user)
  }

  async function handleSubmit() {
    const normalizedTasks = tasks.map((task) => task.task.trim()).filter(Boolean)
    const validationError = validateFlashTodoCreate({
      title,
      businessUnitId,
      assignedTo,
      taskCount: normalizedTasks.length,
    })
    if (validationError) {
      setFeedback({ variant: 'error', message: validationError })
      return
    }

    for (const taskValue of normalizedTasks) {
      const taskError = validateTask(taskValue)
      if (taskError) {
        setFeedback({ variant: 'error', message: taskError })
        return
      }
    }

    let endAt: string | null = null
    if (hasDeadline) {
      const dueAt = applyDueAtFromFields(limitDate, limitHours, limitMinutes)
      if (!dueAt) {
        setFeedback({ variant: 'error', message: 'Choisissez une échéance valide.' })
        return
      }
      endAt = dueAt.toISOString()
    }

    setFeedback(null)

    try {
      const execution = await createMutation.mutateAsync({
        title: title.trim(),
        description: description.trim(),
        business_unit_id: businessUnitId,
        assigned_to: assignedTo,
        end_at: endAt,
        tasks: normalizedTasks.map((taskValue) => ({ task: taskValue })),
      })
      navigate(`/checklists/executions/${execution.id}`, { replace: true })
    } catch (error) {
      setFeedback({
        variant: 'error',
        message: resolveChecklistErrorMessage(error, 'Le Flash To-do n’a pas pu être créé.'),
      })
    }
  }

  return (
    <div className="space-y-3 px-3 pb-28 pt-3">
      <p className="text-sm leading-6 text-[#7D7B75]">
        Créez un Flash To-do et démarrez son exécution immédiatement, sans enregistrer de modèle.
      </p>

      {feedback ? <ChecklistFeedback variant={feedback.variant} message={feedback.message} /> : null}

      <section className="space-y-1.5">
        <TerrainSectionLabel>Titre</TerrainSectionLabel>
        <TerrainCard>
          <Input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Ex. Vérifier la terrasse"
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

      <ChecklistBusinessUnitSelect
        establishmentId={establishmentId}
        selectedBusinessUnitId={businessUnitId}
        onBusinessUnitChange={setBusinessUnitId}
      />

      <ActionCreateAssigneeSection
        establishmentId={establishmentId}
        businessUnitId={businessUnitId || undefined}
        assignedTo={assignedTo}
        selectedUser={selectedUser}
        onAssignedToChange={handleAssigneeChange}
      />

      <ChecklistTaskDraftEditor tasks={tasks} onTasksChange={setTasks} />

      <section className="space-y-2">
        {!hasDeadline ? (
          <Button
            type="button"
            variant="outline"
            className="h-10 w-full rounded-xl border-[#E8E6DF]"
            onClick={enableDeadline}
          >
            Ajouter une échéance
          </Button>
        ) : (
          <div className="space-y-2">
            <ActionCreateDeadlineSection
              selectedPreset={selectedPreset}
              limitDate={limitDate}
              limitHours={limitHours}
              limitMinutes={limitMinutes}
              onPresetChange={handlePresetChange}
              onLimitDateChange={handleLimitDateChange}
              onLimitTimeChange={handleLimitTimeChange}
            />
            <Button
              type="button"
              variant="ghost"
              className="h-9 w-full text-sm text-[#7D7B75]"
              onClick={() => setHasDeadline(false)}
            >
              Retirer l&apos;échéance
            </Button>
          </div>
        )}
      </section>

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
