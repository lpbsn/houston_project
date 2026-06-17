import { LoaderCircle } from 'lucide-react'
import { useRef, useState } from 'react'

import { useAppRoute } from '@/app/app-routes'
import { useAuth } from '@/app/auth-provider'
import { TerrainCard, TerrainErrorState, TerrainSectionLabel } from '@/components/ui/terrain'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ChecklistAssignmentSection } from '@/features/checklists/components/checklist-assignment-section'
import { ChecklistBusinessUnitSelect } from '@/features/checklists/components/checklist-business-unit-select'
import { ChecklistFeedback } from '@/features/checklists/components/checklist-feedback'
import { ChecklistTaskEditor } from '@/features/checklists/components/checklist-task-editor'
import { ChecklistTemplateScheduleOptions } from '@/features/checklists/components/checklist-template-schedule-options'
import { useChecklistTemplateDetailQuery, useUpdateChecklistTemplateMutation } from '@/features/checklists/hooks'
import { resolveChecklistErrorMessage } from '@/features/checklists/lib/checklist-errors'
import {
  canShowChecklistTemplateCreateAssignment,
  canShowChecklistTemplateLaunchExecution,
  canShowChecklistTemplateManageTasks,
  canShowChecklistTemplateUpdate,
} from '@/features/checklists/lib/checklist-template-permission-hints'
import { terrain } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

type ChecklistTemplateDetailPageProps = {
  templateId: string
}

export function ChecklistTemplateDetailPage({ templateId }: ChecklistTemplateDetailPageProps) {
  const { navigate } = useAppRoute()
  const { activeMembership, bootstrap } = useAuth()
  const establishmentId = activeMembership?.establishment_id ?? null

  const detailQuery = useChecklistTemplateDetailQuery(establishmentId, templateId)
  const updateMutation = useUpdateChecklistTemplateMutation(establishmentId ?? '', templateId)

  const assignmentsSectionRef = useRef<HTMLElement>(null)
  const [scheduleFooterHost, setScheduleFooterHost] = useState<HTMLDivElement | null>(null)

  const [titleDraft, setTitleDraft] = useState<string | null>(null)
  const [descriptionDraft, setDescriptionDraft] = useState<string | null>(null)
  const [feedback, setFeedback] = useState<{ variant: 'error' | 'success'; message: string } | null>(
    null,
  )

  if (!establishmentId) {
    return null
  }

  if (detailQuery.isLoading) {
    return (
      <div className="flex items-center justify-center gap-2 px-3 py-10 text-sm text-[#7D7B75]">
        <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden />
        Chargement de la checklist...
      </div>
    )
  }

  if (detailQuery.isError || !detailQuery.data) {
    return (
      <TerrainErrorState
        className="mx-3 mt-3"
        message={resolveChecklistErrorMessage(
          detailQuery.error,
          'Cette checklist est introuvable ou inaccessible.',
        )}
        onRetry={() => void detailQuery.refetch()}
      />
    )
  }

  const template = detailQuery.data
  const title = titleDraft ?? template.title
  const description = descriptionDraft ?? template.description
  const permissionHints = template.permission_hints
  const canUpdateTemplate = canShowChecklistTemplateUpdate(permissionHints)
  const canManageTasks = canShowChecklistTemplateManageTasks(permissionHints)
  const canLaunchExecution = canShowChecklistTemplateLaunchExecution(permissionHints)
  const canCreateAssignment = canShowChecklistTemplateCreateAssignment(permissionHints)
  const showScheduleOptions = canLaunchExecution || canCreateAssignment
  const isBusy = updateMutation.isPending

  async function handleSaveMetadata() {
    setFeedback(null)
    try {
      await updateMutation.mutateAsync({
        title: title.trim(),
        description: description.trim(),
      })
      setTitleDraft(null)
      setDescriptionDraft(null)
      setFeedback({ variant: 'success', message: 'Checklist mise à jour.' })
    } catch (error) {
      setFeedback({
        variant: 'error',
        message: resolveChecklistErrorMessage(error, 'La checklist n’a pas pu être mise à jour.'),
      })
    }
  }

  function handleAssignmentCreated() {
    setFeedback({ variant: 'success', message: 'Affectation créée.' })
    assignmentsSectionRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  const taskCountLabel = (
    <p className={cn('text-xs', terrain.mutedLight)}>
      {template.tasks.length} tâche{template.tasks.length > 1 ? 's' : ''}
    </p>
  )

  const feedbackBanner = feedback ? (
    <ChecklistFeedback variant={feedback.variant} message={feedback.message} />
  ) : null

  const assignmentSection = template.business_unit ? (
    <ChecklistAssignmentSection
      ref={assignmentsSectionRef}
      establishmentId={establishmentId}
      templateId={templateId}
      canCreateAssignment={false}
      businessUnitId={template.business_unit.id}
    />
  ) : null

  const scheduleOptions =
    showScheduleOptions && template.business_unit ? (
      <ChecklistTemplateScheduleOptions
        establishmentId={establishmentId}
        templateId={templateId}
        businessUnitId={template.business_unit.id}
        permissionHints={permissionHints}
        activeMembershipId={activeMembership?.id ?? ''}
        activeMembershipDisplayName={bootstrap?.user?.username ?? null}
        footerHost={scheduleFooterHost}
        onExecutionCreated={(executionId) =>
          navigate(`/checklists/executions/${executionId}`, { replace: true })
        }
        onAssignmentCreated={handleAssignmentCreated}
      />
    ) : null

  const metadataSection = (
    <>
      <section className="space-y-1.5">
        <TerrainSectionLabel>Titre</TerrainSectionLabel>
        <TerrainCard>
          <Input
            value={title}
            onChange={(e) => setTitleDraft(e.target.value)}
            readOnly={!canUpdateTemplate}
            className="border-0 bg-transparent p-0 text-[15px] shadow-none focus-visible:ring-0"
          />
        </TerrainCard>
      </section>

      <section className="space-y-1.5">
        <TerrainSectionLabel>Description</TerrainSectionLabel>
        <TerrainCard>
          <textarea
            value={description}
            onChange={(e) => setDescriptionDraft(e.target.value)}
            readOnly={!canUpdateTemplate}
            className="min-h-[88px] w-full resize-y bg-transparent text-[14px] leading-relaxed text-[#444] outline-none"
          />
        </TerrainCard>
      </section>

      {template.business_unit ? (
        <ChecklistBusinessUnitSelect
          establishmentId={establishmentId}
          selectedBusinessUnitId={template.business_unit.id}
          onBusinessUnitChange={() => undefined}
          readOnlyLabel={template.business_unit.label}
        />
      ) : null}

      {canUpdateTemplate ? (
        <Button
          type="button"
          variant="outline"
          className="h-10 w-full rounded-xl border-[#E8E6DF]"
          disabled={isBusy}
          onClick={() => void handleSaveMetadata()}
        >
          Enregistrer les informations
        </Button>
      ) : null}
    </>
  )

  const tasksSection = canManageTasks ? (
    <ChecklistTaskEditor
      establishmentId={establishmentId}
      templateId={templateId}
      tasks={template.tasks}
    />
  ) : (
    <section className="space-y-2">
      <TerrainSectionLabel>Tâches</TerrainSectionLabel>
      <TerrainCard className="divide-y divide-[#F0EFE9] p-0">
        {template.tasks.map((task, index) => (
          <div key={task.id} className="px-4 py-3.5 text-sm text-[#1a1a1a]">
            {index + 1}. {task.task}
          </div>
        ))}
      </TerrainCard>
    </section>
  )

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="min-h-0 flex-1 overflow-y-auto overscroll-y-contain px-3 pt-3 pb-3">
        <div className="space-y-3">
          {taskCountLabel}
          {feedbackBanner}
          {metadataSection}
          {tasksSection}
          {assignmentSection}
          {scheduleOptions}
        </div>
      </div>
      {showScheduleOptions ? <div ref={setScheduleFooterHost} className="shrink-0" /> : null}
    </div>
  )
}
