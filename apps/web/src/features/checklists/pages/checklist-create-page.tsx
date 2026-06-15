import { LoaderCircle } from 'lucide-react'
import { useMemo, useState } from 'react'

import { useAppRoute } from '@/app/app-routes'
import { useAuth } from '@/app/auth-provider'
import { TerrainCard, TerrainSectionLabel, TerrainStickyFooter } from '@/components/ui/terrain'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useBusinessUnitTreeQuery } from '@/features/auth/hooks'
import { ChecklistCreateBusinessUnitField } from '@/features/checklists/components/checklist-create-business-unit-field'
import { ChecklistCreateFormHeader } from '@/features/checklists/components/checklist-create-form-header'
import {
  ChecklistCreateOptionsButton,
  ChecklistCreateOptionsSheet,
} from '@/features/checklists/components/checklist-create-options-sheet'
import { ChecklistFeedback } from '@/features/checklists/components/checklist-feedback'
import {
  ChecklistTaskDraftEditor,
  createChecklistTaskDraft,
} from '@/features/checklists/components/checklist-task-draft-editor'
import { useChecklistCreateSubmit } from '@/features/checklists/hooks/use-checklist-create-submit'
import {
  buildInitialAssigneeFromMembership,
  type ChecklistCreateAssignmentMode,
} from '@/features/checklists/lib/checklist-create-submit'
import {
  EMPTY_ASSIGNMENT_FORM_VALUES,
  useChecklistAssignmentForm,
} from '@/features/checklists/lib/checklist-assignment-form'
import { validateChecklistCreateForm } from '@/features/checklists/lib/checklist-form-validation'
import { cn } from '@/lib/utils'

type ChecklistCreatePageProps = {
  backPath: string
  initialFlashEnabled?: boolean
}

export function ChecklistCreatePage({
  backPath,
  initialFlashEnabled = false,
}: ChecklistCreatePageProps) {
  const { navigate } = useAppRoute()
  const { activeMembership, bootstrap } = useAuth()
  const establishmentId = activeMembership?.establishment_id ?? null
  const membershipId = activeMembership?.id ?? ''

  const initialAssignee = useMemo(
    () =>
      membershipId
        ? buildInitialAssigneeFromMembership({
            membershipId,
            displayName: bootstrap?.user?.username ?? null,
            username: bootstrap?.user?.username ?? null,
            role: activeMembership?.role ?? null,
          })
        : null,
    [activeMembership?.role, bootstrap?.user?.username, membershipId],
  )

  const [flashEnabled, setFlashEnabled] = useState(initialFlashEnabled)
  const [optionsOpen, setOptionsOpen] = useState(false)
  const [businessUnitSheetOpen, setBusinessUnitSheetOpen] = useState(false)
  const [businessUnitError, setBusinessUnitError] = useState<string | null>(null)
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [businessUnitId, setBusinessUnitId] = useState('')
  const [assignmentMode, setAssignmentMode] =
    useState<ChecklistCreateAssignmentMode>('none')
  const [tasks, setTasks] = useState([createChecklistTaskDraft()])
  const [feedback, setFeedback] = useState<{ variant: 'error' | 'success'; message: string } | null>(
    null,
  )
  const [optionsFieldErrors, setOptionsFieldErrors] = useState<Record<string, string>>({})

  const assignmentForm = useChecklistAssignmentForm({
    initialValues: initialAssignee
      ? { ...EMPTY_ASSIGNMENT_FORM_VALUES, assignedTo: initialAssignee.assignedTo }
      : EMPTY_ASSIGNMENT_FORM_VALUES,
    initialSelectedUser: initialAssignee?.selectedUser ?? null,
  })

  const businessUnitQuery = useBusinessUnitTreeQuery(establishmentId, { staleTime: 60_000 })
  const businessUnitLabel =
    businessUnitQuery.data?.business_units.find((unit) => unit.id === businessUnitId)?.label ??
    null

  const { submit, createdTemplateId, partialFailureMessage, isSubmitting } =
    useChecklistCreateSubmit({
      establishmentId: establishmentId ?? '',
      activeMembershipId: membershipId,
      onNavigate: navigate,
    })

  if (!establishmentId || !membershipId) {
    return null
  }

  const assignmentSummary = flashEnabled
    ? 'Flash to-do'
    : assignmentMode === 'create_now'
      ? 'Affectation configurée'
      : 'Sans affectation'

  async function handleSubmit() {
    const taskValues = tasks.map((task) => task.task)
    const validation = validateChecklistCreateForm({
      flashEnabled,
      title,
      businessUnitId,
      taskValues,
      assignmentMode,
      assignmentValues:
        assignmentMode === 'create_now'
          ? assignmentForm.getFormValues()
          : undefined,
    })

    if (validation.ok === false) {
      setFeedback({ variant: 'error', message: validation.message })
      if (validation.openBusinessUnitSheet) {
        setBusinessUnitSheetOpen(true)
        setBusinessUnitError(validation.message)
      }
      if (validation.openOptions) {
        setOptionsOpen(true)
      }
      if (validation.assignmentErrors) {
        setOptionsFieldErrors(validation.assignmentErrors)
      }
      return
    }

    setBusinessUnitError(null)

    setFeedback(null)

    try {
      await submit({
        title,
        description,
        businessUnitId,
        tasks: taskValues.map((task) => task.trim()).filter(Boolean),
        flashEnabled,
        assignmentMode: flashEnabled ? 'none' : assignmentMode,
        assignmentValues:
          !flashEnabled && assignmentMode === 'create_now'
            ? assignmentForm.getFormValues()
            : undefined,
      })
    } catch (error) {
      const message =
        error instanceof Error ? error.message : 'La création a échoué.'
      setFeedback({ variant: 'error', message })
    }
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <ChecklistCreateFormHeader
        onCancel={() => navigate(backPath)}
        isPending={isSubmitting}
      />

      <div className="min-h-0 flex-1 overflow-y-auto overscroll-y-contain px-3 py-3">
        <div className="space-y-3">
          {feedback ? <ChecklistFeedback variant={feedback.variant} message={feedback.message} /> : null}

          {createdTemplateId ? (
            <TerrainCard className="space-y-2 text-sm">
              <p className="text-[#1a1a1a]">
                La checklist a été créée, mais l’affectation a échoué.
              </p>
              {partialFailureMessage ? (
                <p className="text-xs text-[#7D7B75]">{partialFailureMessage}</p>
              ) : null}
              <div className="flex flex-col gap-2">
                <Button
                  type="button"
                  variant="outline"
                  className="h-10 w-full rounded-xl"
                  onClick={() => navigate(`/checklists/${createdTemplateId}`)}
                >
                  Voir la checklist
                </Button>
                <Button
                  type="button"
                  className="h-10 w-full rounded-xl bg-[#1B4FD8] text-white"
                  disabled={isSubmitting}
                  onClick={() => void handleSubmit()}
                >
                  Réessayer l’affectation
                </Button>
              </div>
            </TerrainCard>
          ) : null}

          <TerrainCard className="flex items-center justify-between gap-3 px-3 py-2.5">
            <div>
              <p className="text-sm font-medium text-[#1a1a1a]">Flash to-do</p>
              <p className="text-xs text-[#7D7B75]">
                Démarrer immédiatement sans enregistrer de modèle.
              </p>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={flashEnabled}
              aria-label="Flash to-do"
              className={cn(
                'relative h-7 w-12 shrink-0 rounded-full transition-colors',
                flashEnabled ? 'bg-[#1B4FD8]' : 'bg-[#D8D6CF]',
              )}
              onClick={() => setFlashEnabled((current) => !current)}
            >
              <span
                className={cn(
                  'absolute top-0.5 h-6 w-6 rounded-full bg-white shadow transition-transform',
                  flashEnabled ? 'translate-x-5' : 'translate-x-0.5',
                )}
              />
            </button>
          </TerrainCard>

          <ChecklistCreateBusinessUnitField
            establishmentId={establishmentId}
            selectedBusinessUnitId={businessUnitId}
            selectedBusinessUnitLabel={businessUnitLabel}
            error={businessUnitError}
            open={businessUnitSheetOpen}
            onOpenChange={setBusinessUnitSheetOpen}
            onBusinessUnitChange={(value) => {
              setBusinessUnitId(value)
              setBusinessUnitError(null)
            }}
          />

          <section className="space-y-1.5">
            <TerrainSectionLabel>Titre</TerrainSectionLabel>
            <TerrainCard>
              <Input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="To do ouverture"
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

          <ChecklistCreateOptionsButton
            assignmentSummary={assignmentSummary}
            onClick={() => setOptionsOpen(true)}
          />
        </div>
      </div>

      <TerrainStickyFooter>
        <Button
          type="button"
          className="h-11 w-full rounded-xl bg-[#1B4FD8] text-white hover:bg-[#1B4FD8]/95"
          disabled={isSubmitting}
          onClick={() => void handleSubmit()}
        >
          {isSubmitting ? (
            <LoaderCircle className="mr-2 h-4 w-4 animate-spin" aria-hidden />
          ) : null}
          Créer
        </Button>
      </TerrainStickyFooter>

      <ChecklistCreateOptionsSheet
        open={optionsOpen}
        flashEnabled={flashEnabled}
        establishmentId={establishmentId}
        businessUnitId={businessUnitId}
        assignmentMode={assignmentMode}
        onAssignmentModeChange={setAssignmentMode}
        assignedTo={assignmentForm.assignedTo}
        selectedUser={assignmentForm.selectedUser}
        onAssignedToChange={(membershipIdValue, user) => {
          assignmentForm.setAssignedTo(membershipIdValue)
          assignmentForm.setSelectedUser(user)
        }}
        startDate={assignmentForm.startDate}
        onStartDateChange={assignmentForm.setStartDate}
        endDate={assignmentForm.endDate}
        onEndDateChange={assignmentForm.setEndDate}
        startAt={assignmentForm.startAt}
        onStartAtChange={assignmentForm.setStartAt}
        endAt={assignmentForm.endAt}
        onEndAtChange={assignmentForm.setEndAt}
        recurrenceDays={assignmentForm.recurrenceDays}
        onRecurrenceDaysChange={assignmentForm.setRecurrenceDays}
        fieldErrors={optionsFieldErrors}
        onFieldErrorsChange={setOptionsFieldErrors}
        onClose={() => setOptionsOpen(false)}
        onSave={() => setOptionsOpen(false)}
      />
    </div>
  )
}
