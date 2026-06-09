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
import { useCreateRegisteredChecklistTemplateMutation } from '@/features/checklists/hooks'
import { resolveChecklistErrorMessage } from '@/features/checklists/lib/checklist-errors'
import {
  validateRegisteredTemplateCreate,
  validateTask,
} from '@/features/checklists/lib/checklist-form-validation'
import type { ChecklistBadge } from '@/features/checklists/types'
import { cn } from '@/lib/utils'

export function ChecklistTemplateCreatePage() {
  const { navigate } = useAppRoute()
  const { activeMembership } = useAuth()
  const establishmentId = activeMembership?.establishment_id ?? null

  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [businessUnitId, setBusinessUnitId] = useState('')
  const [badge, setBadge] = useState<ChecklistBadge>('todo')
  const [tasks, setTasks] = useState([createChecklistTaskDraft()])
  const [assignNow, setAssignNow] = useState(false)
  const [assignedTo, setAssignedTo] = useState(activeMembership?.id ?? '')
  const [selectedUser, setSelectedUser] = useState<ScopedUserSearchResult | null>(null)
  const [hasDeadline, setHasDeadline] = useState(false)
  const [selectedPreset, setSelectedPreset] = useState<DeadlinePreset | null>('2h')
  const [limitDate, setLimitDate] = useState('')
  const [limitHours, setLimitHours] = useState('')
  const [limitMinutes, setLimitMinutes] = useState('')
  const [feedback, setFeedback] = useState<{ variant: 'error' | 'success'; message: string } | null>(
    null,
  )

  const createMutation = useCreateRegisteredChecklistTemplateMutation(establishmentId ?? '')

  if (!establishmentId) {
    return null
  }

  function badgeButtonClass(isSelected: boolean): string {
    return cn(
      'rounded-full px-3 py-1.5 text-xs font-medium transition-colors',
      isSelected
        ? 'bg-[#EEF2FF] text-[#1B4FD8]'
        : 'bg-[#F5F4F0] text-[#555] hover:bg-[#EBEAE4]',
    )
  }

  function handleAssigneeChange(membershipId: string, user: ScopedUserSearchResult) {
    setAssignedTo(membershipId)
    setSelectedUser(user)
  }

  async function handleSubmit() {
    const normalizedTasks = tasks.map((task) => task.task.trim()).filter(Boolean)
    const validationError = validateRegisteredTemplateCreate({
      title,
      businessUnitId,
      taskCount: normalizedTasks.length,
      assignNow,
      assignedTo,
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
    if (assignNow && hasDeadline) {
      const hours = Number.parseInt(limitHours, 10)
      const minutes = Number.parseInt(limitMinutes, 10)
      const dueAt = buildDueAtFromParts(limitDate, hours, minutes)
      if (!dueAt) {
        setFeedback({ variant: 'error', message: 'Choisissez une échéance valide.' })
        return
      }
      endAt = dueAt.toISOString()
    }

    setFeedback(null)

    try {
      const result = await createMutation.mutateAsync({
        title: title.trim(),
        description: description.trim(),
        business_unit_id: businessUnitId,
        badge,
        tasks: normalizedTasks.map((taskValue) => ({ task: taskValue })),
        assign_now: assignNow,
        assigned_to: assignNow ? assignedTo : null,
        end_at: assignNow ? endAt : null,
      })

      if (assignNow && result.id) {
        navigate('/checklists', { replace: true })
        return
      }

      navigate(`/checklists/${result.id}`, { replace: true })
    } catch (error) {
      setFeedback({
        variant: 'error',
        message: resolveChecklistErrorMessage(error, 'La checklist n’a pas pu être créée.'),
      })
    }
  }

  return (
    <div className="space-y-3 px-3 pb-28 pt-3">
      {feedback ? <ChecklistFeedback variant={feedback.variant} message={feedback.message} /> : null}

      <ChecklistBusinessUnitSelect
        establishmentId={establishmentId}
        selectedBusinessUnitId={businessUnitId}
        onBusinessUnitChange={setBusinessUnitId}
      />

      <section className="space-y-2">
        <TerrainSectionLabel>Badge</TerrainSectionLabel>
        <div className="flex flex-wrap gap-2">
          {(['todo', 'process'] as const).map((value) => (
            <button
              key={value}
              type="button"
              className={badgeButtonClass(badge === value)}
              onClick={() => setBadge(value)}
            >
              {value === 'process' ? 'Process' : 'To-do'}
            </button>
          ))}
        </div>
      </section>

      <section className="space-y-1.5">
        <TerrainSectionLabel>Titre</TerrainSectionLabel>
        <TerrainCard>
          <Input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Ex. Fermeture restaurant"
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

      <section className="space-y-2">
        <button
          type="button"
          className={cn(
            'flex min-h-11 w-full items-center justify-between rounded-lg border px-3 py-2.5 text-left',
            assignNow ? 'border-[#1B4FD8] bg-[#EEF4FF]' : 'border-[#E8E6DF] bg-[#F5F4F0]',
          )}
          onClick={() => setAssignNow((current) => !current)}
        >
          <span className="text-sm font-medium text-[#1a1a1a]">Assigner maintenant</span>
          <span className="text-xs text-[#7D7B75]">{assignNow ? 'Oui' : 'Non'}</span>
        </button>

        {assignNow ? (
          <div className="space-y-3">
            <ActionCreateAssigneeSection
              establishmentId={establishmentId}
              businessUnitId={businessUnitId || undefined}
              assignedTo={assignedTo}
              selectedUser={selectedUser}
              onAssignedToChange={handleAssigneeChange}
            />
            {!hasDeadline ? (
              <Button
                type="button"
                variant="outline"
                className="h-10 w-full rounded-xl border-[#E8E6DF]"
                onClick={() => {
                  const initialDue = applyDeadlinePreset('2h', new Date())
                  const synced = syncDeadlineFieldsFromDueAt(initialDue)
                  setHasDeadline(true)
                  setSelectedPreset('2h')
                  setLimitDate(synced.limitDate)
                  setLimitHours(synced.limitHours)
                  setLimitMinutes(synced.limitMinutes)
                }}
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
                  onPresetChange={(preset) => {
                    const next = applyDeadlinePreset(preset, new Date())
                    const synced = syncDeadlineFieldsFromDueAt(next)
                    setSelectedPreset(preset)
                    setLimitDate(synced.limitDate)
                    setLimitHours(synced.limitHours)
                    setLimitMinutes(synced.limitMinutes)
                  }}
                  onLimitDateChange={(value) => {
                    setLimitDate(value)
                    setSelectedPreset(null)
                  }}
                  onLimitTimeChange={(hours, minutes) => {
                    setLimitHours(hours)
                    setLimitMinutes(minutes)
                    setSelectedPreset(null)
                  }}
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
          </div>
        ) : null}
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
        Créer la checklist
      </Button>
    </div>
  )
}
