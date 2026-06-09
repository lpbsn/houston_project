import { LoaderCircle, Trash2 } from 'lucide-react'

import { TerrainCard } from '@/components/layout/terrain-card'
import { canShowChecklistTemplateDelete } from '@/features/checklists/lib/checklist-template-permission-hints'
import type { ChecklistTemplateListItem } from '@/features/checklists/types'
import { terrain } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

const DELETE_CONFIRM_MESSAGE =
  'Supprimer définitivement cette checklist ? Cette action est irréversible.'

type ChecklistTemplateSectionProps = {
  templates: ChecklistTemplateListItem[] | undefined
  isLoading: boolean
  isError: boolean
  emptyTitle: string
  emptyDescription: string
  onOpenTemplate: (templateId: string) => void
  onDeleteTemplate?: (templateId: string) => void
  deletingTemplateId?: string | null
}

export function ChecklistTemplateSection({
  templates,
  isLoading,
  isError,
  emptyTitle,
  emptyDescription,
  onOpenTemplate,
  onDeleteTemplate,
  deletingTemplateId,
}: ChecklistTemplateSectionProps) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center gap-2 py-6 text-sm text-[#7D7B75]">
        <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden />
        Chargement...
      </div>
    )
  }

  if (isError) {
    return (
      <TerrainCard className={terrain.errorSurface}>
        <p className="text-sm">Les checklists n&apos;ont pas pu être chargées. Réessayez plus tard.</p>
      </TerrainCard>
    )
  }

  const items = templates ?? []

  function handleDelete(templateId: string) {
    if (!onDeleteTemplate) {
      return
    }
    if (!window.confirm(DELETE_CONFIRM_MESSAGE)) {
      return
    }
    onDeleteTemplate(templateId)
  }

  if (items.length === 0) {
    return (
      <TerrainCard className="space-y-2 py-6 text-center">
        <p className="text-sm font-semibold text-[#1a1a1a]">{emptyTitle}</p>
        <p className={cn('text-xs leading-5', terrain.muted)}>{emptyDescription}</p>
      </TerrainCard>
    )
  }

  return (
    <TerrainCard className="divide-y divide-[#F0EFE9] p-0">
      {items.map((template) => {
        const isDeleting = deletingTemplateId === template.id
        const showDelete =
          Boolean(onDeleteTemplate) && canShowChecklistTemplateDelete(template.permission_hints)

        return (
          <div key={template.id} className="flex items-stretch">
            <button
              type="button"
              onClick={() => onOpenTemplate(template.id)}
              className="min-w-0 flex-1 px-4 py-3.5 text-left transition-colors hover:bg-[#FAFAF8]"
            >
              <p className="text-sm font-semibold text-[#1a1a1a]">{template.title}</p>
              {template.description ? (
                <p className={cn('mt-0.5 line-clamp-2 text-xs leading-5', terrain.muted)}>
                  {template.description}
                </p>
              ) : null}
              {template.business_unit ? (
                <p className={cn('mt-1 text-[11px]', terrain.mutedLight)}>
                  {template.business_unit.label}
                </p>
              ) : null}
              <p className={cn('mt-1.5 text-[11px]', terrain.mutedLight)}>
                {template.task_count} tâche{template.task_count > 1 ? 's' : ''}
              </p>
            </button>
            {showDelete ? (
              <button
                type="button"
                className="flex shrink-0 items-center px-3 text-[#E24B4A] transition-colors hover:bg-[#FFF5F3] disabled:opacity-40"
                aria-label="Supprimer la checklist"
                disabled={isDeleting}
                onClick={() => handleDelete(template.id)}
              >
                {isDeleting ? (
                  <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden />
                ) : (
                  <Trash2 className="h-4 w-4" />
                )}
              </button>
            ) : null}
          </div>
        )
      })}
    </TerrainCard>
  )
}
