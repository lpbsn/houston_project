import { LoaderCircle } from 'lucide-react'
import { forwardRef, useMemo, useState } from 'react'

import { useAppRoute } from '@/app/app-routes'
import { TerrainCard, TerrainSectionLabel } from '@/components/ui/terrain'
import { Button } from '@/components/ui/button'
import { ChecklistAssignmentCreateSheet } from '@/features/checklists/components/checklist-assignment-create-sheet'
import { ChecklistAssignmentEditSheet } from '@/features/checklists/components/checklist-assignment-edit-sheet'
import { ChecklistFeedback } from '@/features/checklists/components/checklist-feedback'
import {
  useChecklistAssignmentsQuery,
  useDeactivateChecklistAssignmentMutation,
} from '@/features/checklists/hooks'
import {
  CHECKLIST_ASSIGNMENT_REMOVE_CONFIRM_MESSAGE,
  CHECKLIST_ASSIGNMENT_REMOVE_SUCCESS_MESSAGE,
  getActiveExecutionIdFromAssignmentRemoveError,
  resolveChecklistAssignmentRemoveErrorMessage,
} from '@/features/checklists/lib/checklist-assignment-remove-flow'
import {
  canShowChecklistAssignmentDeactivate,
  canShowChecklistAssignmentUpdate,
} from '@/features/checklists/lib/checklist-assignment-permission-hints'
import { formatRecurrenceDaysLabel } from '@/features/checklists/lib/checklist-recurrence'
import type { ChecklistAssignment } from '@/features/checklists/types'
import { terrain } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

type ChecklistAssignmentSectionProps = {
  establishmentId: string
  templateId: string
  canCreateAssignment: boolean
  businessUnitId: string
  createButtonPlacement?: 'inline' | 'sticky'
  isCreateSheetOpen?: boolean
  onCreateSheetOpenChange?: (open: boolean) => void
}

function formatDateLabel(value: string): string {
  const date = new Date(`${value}T00:00:00`)
  if (Number.isNaN(date.getTime())) {
    return value
  }
  return date.toLocaleDateString('fr-FR')
}

function formatTimeLabel(value: string): string {
  return value.slice(0, 5)
}

export const ChecklistAssignmentSection = forwardRef<HTMLElement, ChecklistAssignmentSectionProps>(
  function ChecklistAssignmentSection(
    {
      establishmentId,
      templateId,
      canCreateAssignment,
      businessUnitId,
      createButtonPlacement = 'inline',
      isCreateSheetOpen: isCreateSheetOpenProp,
      onCreateSheetOpenChange,
    },
    ref,
  ) {
  const { navigate } = useAppRoute()
  const assignmentsQuery = useChecklistAssignmentsQuery(establishmentId)
  const deactivateMutation = useDeactivateChecklistAssignmentMutation(establishmentId, templateId)

  const [isCreateSheetOpenInternal, setIsCreateSheetOpenInternal] = useState(false)
  const isCreateSheetOpen = isCreateSheetOpenProp ?? isCreateSheetOpenInternal
  const setIsCreateSheetOpen = onCreateSheetOpenChange ?? setIsCreateSheetOpenInternal
  const showInlineCreateButton =
    canCreateAssignment && createButtonPlacement === 'inline'
  const [editingAssignment, setEditingAssignment] = useState<ChecklistAssignment | null>(null)
  const [feedback, setFeedback] = useState<{ variant: 'error' | 'success'; message: string } | null>(
    null,
  )
  const [removeError, setRemoveError] = useState<string | null>(null)
  const [activeExecutionId, setActiveExecutionId] = useState<string | null>(null)

  const templateAssignments = useMemo(() => {
    return (assignmentsQuery.data ?? []).filter(
      (assignment) => assignment.checklist_template_id === templateId,
    )
  }, [assignmentsQuery.data, templateId])

  async function handleRemove(assignmentId: string) {
    if (!window.confirm(CHECKLIST_ASSIGNMENT_REMOVE_CONFIRM_MESSAGE)) {
      return
    }

    setFeedback(null)
    setRemoveError(null)
    setActiveExecutionId(null)

    try {
      await deactivateMutation.mutateAsync(assignmentId)
      setFeedback({ variant: 'success', message: CHECKLIST_ASSIGNMENT_REMOVE_SUCCESS_MESSAGE })
    } catch (error) {
      setActiveExecutionId(getActiveExecutionIdFromAssignmentRemoveError(error))
      setRemoveError(
        resolveChecklistAssignmentRemoveErrorMessage(
          error,
          'L’affectation n’a pas pu être retirée.',
        ),
      )
    }
  }

  return (
    <section ref={ref} className="space-y-3">
      <TerrainSectionLabel>Affectations</TerrainSectionLabel>

      {feedback ? <ChecklistFeedback variant={feedback.variant} message={feedback.message} /> : null}
      {removeError ? <ChecklistFeedback variant="error" message={removeError} /> : null}
      {activeExecutionId ? (
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="rounded-lg border-[#E8E6DF]"
          onClick={() => navigate(`/checklists/executions/${activeExecutionId}`)}
        >
          Ouvrir l&apos;exécution en cours
        </Button>
      ) : null}

      {assignmentsQuery.isLoading ? (
        <div className="flex items-center gap-2 text-sm text-[#7D7B75]">
          <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden />
          Chargement des affectations…
        </div>
      ) : templateAssignments.length > 0 ? (
        <TerrainCard className="divide-y divide-[#F0EFE9] p-0">
          {templateAssignments.map((assignment) => (
            <div key={assignment.id} className="space-y-2 px-4 py-3.5">
              <div>
                <p className="text-sm font-semibold text-[#1a1a1a]">
                  {assignment.assigned_to_display_name}
                </p>
                <p className={cn('mt-0.5 text-xs', terrain.muted)}>
                  {assignment.business_unit.label}
                </p>
                <p className={cn('mt-1 text-xs', terrain.mutedLight)}>
                  Période : {formatDateLabel(assignment.start_date)} →{' '}
                  {formatDateLabel(assignment.end_date)}
                </p>
                <p className={cn('text-xs', terrain.mutedLight)}>
                  Horaires : {formatTimeLabel(assignment.start_at)} –{' '}
                  {formatTimeLabel(assignment.end_at)}
                </p>
                <p className={cn('text-xs', terrain.mutedLight)}>
                  {formatRecurrenceDaysLabel(assignment.recurrence_days)}
                </p>
              </div>
              {canShowChecklistAssignmentUpdate(assignment.permission_hints) ||
              canShowChecklistAssignmentDeactivate(assignment.permission_hints) ? (
                <div className="flex flex-wrap gap-2">
                  {canShowChecklistAssignmentUpdate(assignment.permission_hints) ? (
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      className="rounded-lg border-[#E8E6DF]"
                      onClick={() => setEditingAssignment(assignment)}
                    >
                      Modifier l&apos;affectation
                    </Button>
                  ) : null}
                  {canShowChecklistAssignmentDeactivate(assignment.permission_hints) ? (
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      className="rounded-lg border-[#E8E6DF] text-[#E24B4A]"
                      disabled={deactivateMutation.isPending}
                      onClick={() => void handleRemove(assignment.id)}
                    >
                      Retirer l&apos;affectation
                    </Button>
                  ) : null}
                </div>
              ) : null}
            </div>
          ))}
        </TerrainCard>
      ) : (
        <TerrainCard className="py-4 text-center">
          <p className={cn('text-sm', terrain.muted)}>Aucune affectation active.</p>
        </TerrainCard>
      )}

      {showInlineCreateButton ? (
        <Button
          type="button"
          className="h-11 w-full rounded-xl bg-[#1B4FD8]"
          onClick={() => setIsCreateSheetOpen(true)}
        >
          Nouvelle affectation
        </Button>
      ) : null}

      {isCreateSheetOpen ? (
        <ChecklistAssignmentCreateSheet
          open
          establishmentId={establishmentId}
          templateId={templateId}
          businessUnitId={businessUnitId}
          onClose={() => setIsCreateSheetOpen(false)}
          onSuccess={() => setFeedback({ variant: 'success', message: 'Affectation créée.' })}
        />
      ) : null}

      {editingAssignment ? (
        <ChecklistAssignmentEditSheet
          open
          establishmentId={establishmentId}
          templateId={templateId}
          businessUnitId={businessUnitId}
          assignment={editingAssignment}
          onClose={() => setEditingAssignment(null)}
          onSuccess={() =>
            setFeedback({
              variant: 'success',
              message:
                'L’affectation a été modifiée. Les exécutions à faire ont été mises à jour.',
            })
          }
        />
      ) : null}
    </section>
  )
},
)
