import { LoaderCircle } from 'lucide-react'
import { useState } from 'react'

import { TerrainBottomSheet } from '@/components/ui/terrain'
import { Button } from '@/components/ui/button'
import { ActionCreateAssigneeSection } from '@/features/actions/components/action-create-assignee-section'
import { ActionCreateDeadlineSection } from '@/features/actions/components/action-create-deadline-section'
import {
  applyDeadlinePreset,
  buildDueAtFromParts,
  syncDeadlineFieldsFromDueAt,
  type DeadlinePreset,
} from '@/features/actions/lib/action-create-deadline'
import type { ScopedUserSearchResult } from '@/features/actions/types'
import { ChecklistFeedback } from '@/features/checklists/components/checklist-feedback'
import { useCreateTemplateExecutionMutation } from '@/features/checklists/hooks'
import { resolveChecklistErrorMessage } from '@/features/checklists/lib/checklist-errors'
import {
  canAssignChecklistExecutionToOthers,
  getChecklistTemplateLaunchButtonLabel,
  type ChecklistTemplatePermissionHints,
} from '@/features/checklists/lib/checklist-template-permission-hints'

type ChecklistTemplateUseSheetProps = {
  open: boolean
  establishmentId: string
  templateId: string
  businessUnitId: string
  permissionHints: ChecklistTemplatePermissionHints
  defaultAssignedTo?: string
  onClose: () => void
  onSuccess: (executionId: string) => void
}

export function ChecklistTemplateUseSheet({
  open,
  establishmentId,
  templateId,
  businessUnitId,
  permissionHints,
  defaultAssignedTo = '',
  onClose,
  onSuccess,
}: ChecklistTemplateUseSheetProps) {
  const canAssignToOthers = canAssignChecklistExecutionToOthers(permissionHints)
  const submitLabel = getChecklistTemplateLaunchButtonLabel(permissionHints)

  const [assignedTo, setAssignedTo] = useState('')
  const [selectedUser, setSelectedUser] = useState<ScopedUserSearchResult | null>(null)
  const [hasDeadline, setHasDeadline] = useState(false)
  const [selectedPreset, setSelectedPreset] = useState<DeadlinePreset | null>('2h')
  const [limitDate, setLimitDate] = useState('')
  const [limitHours, setLimitHours] = useState('')
  const [limitMinutes, setLimitMinutes] = useState('')
  const [feedback, setFeedback] = useState<string | null>(null)

  const launchMutation = useCreateTemplateExecutionMutation(establishmentId, templateId)

  function handleClose() {
    setFeedback(null)
    onClose()
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

  function handleAssigneeChange(membershipId: string, user: ScopedUserSearchResult) {
    setAssignedTo(membershipId)
    setSelectedUser(user)
  }

  async function handleSubmit() {
    const effectiveAssignedTo = canAssignToOthers ? assignedTo : defaultAssignedTo

    if (!effectiveAssignedTo.trim()) {
      setFeedback('Sélectionnez un membre assigné.')
      return
    }

    let endAt: string | null = null
    if (hasDeadline) {
      const hours = Number.parseInt(limitHours, 10)
      const minutes = Number.parseInt(limitMinutes, 10)
      const dueAt = buildDueAtFromParts(limitDate, hours, minutes)
      if (!dueAt) {
        setFeedback('Choisissez une échéance valide.')
        return
      }
      endAt = dueAt.toISOString()
    }

    setFeedback(null)

    try {
      const execution = await launchMutation.mutateAsync({
        assigned_to: effectiveAssignedTo,
        end_at: endAt,
      })
      handleClose()
      onSuccess(execution.id)
    } catch (error) {
      setFeedback(
        resolveChecklistErrorMessage(error, 'L’exécution n’a pas pu être lancée.'),
      )
    }
  }

  return (
    <TerrainBottomSheet title="Utiliser cette checklist" open={open} onClose={handleClose}>
      <div className="space-y-3 pb-2">
        <p className="text-xs leading-5 text-[#7D7B75]">
          {canAssignToOthers
            ? 'Choisissez un assigné pour lancer une exécution depuis ce modèle.'
            : 'Lancez une exécution pour vous depuis ce modèle.'}
        </p>

        {feedback ? <ChecklistFeedback variant="error" message={feedback} /> : null}

        {canAssignToOthers ? (
          <ActionCreateAssigneeSection
            establishmentId={establishmentId}
            businessUnitId={businessUnitId}
            assignedTo={assignedTo}
            selectedUser={selectedUser}
            onAssignedToChange={handleAssigneeChange}
          />
        ) : null}

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

        <Button
          type="button"
          className="h-11 w-full rounded-xl bg-[#1D9E75] text-white hover:bg-[#1D9E75]/95"
          disabled={launchMutation.isPending}
          onClick={() => void handleSubmit()}
        >
          {launchMutation.isPending ? (
            <LoaderCircle className="mr-2 h-4 w-4 animate-spin" aria-hidden />
          ) : null}
          {submitLabel}
        </Button>
      </div>
    </TerrainBottomSheet>
  )
}
