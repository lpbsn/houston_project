import { HoustonBadge, TerrainCard } from '@/components/ui/terrain'
import { getDisplayNameInitials } from '@/lib/display-names'

import {
  buildActionPlanExecutionClassificationDisplay,
  formatActionPlanCreatedAtLabel,
} from '../lib/action-plan-display'
import type { ActionPlanExecutionDetail } from '../types'
import { ActionPlanStatusBadge } from './action-plan-status-badge'

type ActionPlanExecutionDetailTitleSectionProps = {
  execution: ActionPlanExecutionDetail
}

export function ActionPlanExecutionDetailTitleSection({
  execution,
}: ActionPlanExecutionDetailTitleSectionProps) {
  const classification = buildActionPlanExecutionClassificationDisplay(execution)
  const createdAtLabel = formatActionPlanCreatedAtLabel(execution.created_at)
  const locationText = execution.signal_summary?.location_text?.trim() || null
  const creatorInitials = getDisplayNameInitials(execution.created_by_display_name)

  return (
    <TerrainCard className="space-y-2">
      <div className="flex items-start justify-between gap-2">
        <h1 className="text-[17px] font-semibold leading-snug text-[#1a1a1a]">{execution.title}</h1>
        <ActionPlanStatusBadge status={execution.status} />
      </div>

      <div className="flex items-center gap-2">
        <div
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[#E8F5E9] text-[11px] font-bold text-[#2E7D32]"
          aria-hidden
        >
          {creatorInitials}
        </div>
        <p className="text-xs text-[#7D7B75]">
          Créé par <span className="font-medium text-[#1a1a1a]">{execution.created_by_display_name}</span>
          {createdAtLabel ? (
            <>
              <span aria-hidden> · </span>
              <span>{createdAtLabel}</span>
            </>
          ) : null}
        </p>
      </div>

      {classification.poleLabel || classification.subjectLabel ? (
        <div className="flex flex-wrap gap-1.5">
          {classification.poleLabel ? (
            <HoustonBadge variant="gray" className="text-[10px]">
              {classification.poleLabel}
            </HoustonBadge>
          ) : null}
          {classification.subjectLabel ? (
            <HoustonBadge variant="gray" className="bg-[#F0EFE9] text-[10px] text-[#555]">
              {classification.subjectLabel}
            </HoustonBadge>
          ) : null}
        </div>
      ) : null}

      {locationText ? (
        <p className="text-[12px] text-[#888]">
          <span className="text-[#E24B4A]" aria-hidden>
            📍{' '}
          </span>
          {locationText}
        </p>
      ) : null}
    </TerrainCard>
  )
}
