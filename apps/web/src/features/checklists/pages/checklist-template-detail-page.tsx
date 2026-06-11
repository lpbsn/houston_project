import { LoaderCircle } from 'lucide-react'
import { useState } from 'react'

import { useAppRoute } from '@/app/app-routes'
import { useAuth } from '@/app/auth-provider'
import { TerrainCard, TerrainSectionLabel } from '@/components/ui/terrain'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { HoustonBadge } from '@/components/ui/terrain'
import { ChecklistAssignmentCreateStickyFooter } from '@/features/checklists/components/checklist-assignment-create-sticky-footer'
import { ChecklistAssignmentSection } from '@/features/checklists/components/checklist-assignment-section'
import { ChecklistBusinessUnitSelect } from '@/features/checklists/components/checklist-business-unit-select'
import { ChecklistFeedback } from '@/features/checklists/components/checklist-feedback'
import { ChecklistTaskEditor } from '@/features/checklists/components/checklist-task-editor'
import { ChecklistTemplateUseSheet } from '@/features/checklists/components/checklist-template-use-sheet'
import { useChecklistTemplateDetailQuery, useUpdateChecklistTemplateMutation } from '@/features/checklists/hooks'
import { formatChecklistBadgeLabel } from '@/features/checklists/lib/checklist-display'
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
  const { activeMembership } = useAuth()
  const establishmentId = activeMembership?.establishment_id ?? null

  const detailQuery = useChecklistTemplateDetailQuery(establishmentId, templateId)
  const updateMutation = useUpdateChecklistTemplateMutation(establishmentId ?? '', templateId)

  const [titleDraft, setTitleDraft] = useState<string | null>(null)
  const [descriptionDraft, setDescriptionDraft] = useState<string | null>(null)
  const [feedback, setFeedback] = useState<{ variant: 'error' | 'success'; message: string } | null>(
    null,
  )
  const [isCreateAssignmentOpen, setIsCreateAssignmentOpen] = useState(false)
  const [isUseSheetOpen, setIsUseSheetOpen] = useState(false)

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
      <div className="px-3 py-4">
        <TerrainCard className={terrain.errorSurface}>
          <p className="text-sm">Cette checklist est introuvable ou inaccessible.</p>
          <Button
            type="button"
            variant="outline"
            className="mt-3 rounded-xl"
            onClick={() => navigate('/checklists')}
          >
            Retour à la bibliothèque
          </Button>
        </TerrainCard>
      </div>
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
  const isBusy = updateMutation.isPending
  const showStickyCreateFooter = canCreateAssignment

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

  const taskCountLabel = (
    <div className="flex flex-wrap items-center gap-2">
      <p className={cn('text-xs', terrain.mutedLight)}>
        {template.tasks.length} tâche{template.tasks.length > 1 ? 's' : ''}
      </p>
      <HoustonBadge variant="amber" className="text-[8px]">
        {formatChecklistBadgeLabel(template.badge)}
      </HoustonBadge>
    </div>
  )

  const feedbackBanner = feedback ? (
    <ChecklistFeedback variant={feedback.variant} message={feedback.message} />
  ) : null

  const assignmentSection = template.business_unit ? (
    <ChecklistAssignmentSection
      establishmentId={establishmentId}
      templateId={templateId}
      canCreateAssignment={canCreateAssignment}
      businessUnitId={template.business_unit.id}
      createButtonPlacement="sticky"
      isCreateSheetOpen={isCreateAssignmentOpen}
      onCreateSheetOpenChange={setIsCreateAssignmentOpen}
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

  const launchButton = canLaunchExecution ? (
    <Button
      type="button"
      className="h-11 w-full rounded-xl bg-[#1D9E75] text-white hover:bg-[#1D9E75]/95"
      disabled={isBusy}
      onClick={() => setIsUseSheetOpen(true)}
    >
      Utiliser cette checklist
    </Button>
  ) : null

  return (
    <>
      <ChecklistTemplateUseSheet
        open={isUseSheetOpen}
        establishmentId={establishmentId}
        templateId={templateId}
        businessUnitId={template.business_unit.id}
        defaultAssignedTo={activeMembership?.id ?? ''}
        onClose={() => setIsUseSheetOpen(false)}
        onSuccess={(executionId) => navigate(`/checklists/executions/${executionId}`, { replace: true })}
      />

      <div className="flex min-h-full flex-col">
        <div
          className={cn(
            'flex flex-1 flex-col space-y-3 px-3 pt-3',
            showStickyCreateFooter ? 'pb-40' : 'pb-28',
          )}
        >
          {taskCountLabel}
          {feedbackBanner}
          {launchButton}
          {assignmentSection}
          {metadataSection}
          {tasksSection}
        </div>

        {showStickyCreateFooter ? (
          <ChecklistAssignmentCreateStickyFooter
            onClick={() => setIsCreateAssignmentOpen(true)}
          />
        ) : null}
      </div>
    </>
  )
}
