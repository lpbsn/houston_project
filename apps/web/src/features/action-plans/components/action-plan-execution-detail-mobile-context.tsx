import { TerrainCard } from '@/components/ui/terrain'
import {
  formatActionPlanFeedCanceledLine,
  formatActionPlanFeedMarkedDoneLine,
  formatActionPlanFeedValidatedLine,
} from '@/features/execution/lib/action-plan-execution-feed-card-display'
import { formatCivilDateFr, splitIsoToCivil } from '@/lib/business-timezone'
import { getDisplayNameInitials } from '@/lib/display-names'

import { actionPlanBusinessUnitPrimaryLabel } from '../lib/action-plan-display'
import type { ActionPlanExecutionDetail } from '../types'
import { ActionPlanExecutionDetailAssigneesSection } from './action-plan-execution-detail-assignees-section'
import { ActionPlanExecutionDetailLabel } from './action-plan-execution-detail-label'
import { ActionPlanStatusBadge } from './action-plan-status-badge'

type ActionPlanExecutionDetailMobileContextProps = {
  execution: ActionPlanExecutionDetail
  currentMembershipId?: string | null
}

function creatorLine(name: string, createdAt: string | null): string {
  const civil = createdAt ? splitIsoToCivil(createdAt) : null
  if (!civil?.date || !civil.time) {
    return name
  }
  return `${name} le ${formatCivilDateFr(civil.date)} à ${civil.time}`
}

export function ActionPlanExecutionDetailMobileContext({
  execution,
  currentMembershipId,
}: ActionPlanExecutionDetailMobileContextProps) {
  const pilotLabel = actionPlanBusinessUnitPrimaryLabel(execution.pilot_business_unit).trim()
  const creatorName = execution.created_by_display_name.trim()
  const lifecycleLines = [
    formatActionPlanFeedMarkedDoneLine(execution),
    formatActionPlanFeedValidatedLine(execution),
    formatActionPlanFeedCanceledLine(execution),
  ].filter((line): line is string => Boolean(line))

  return (
    <TerrainCard className="min-w-0">
      <div data-testid="execution-detail-mobile-context" className="space-y-2">
        <div className="flex items-center justify-between gap-2">
          <ActionPlanExecutionDetailLabel>Contexte</ActionPlanExecutionDetailLabel>
          <ActionPlanStatusBadge
            status={execution.status}
            validatedAt={execution.validated_at}
            variant="executionHeader"
          />
        </div>
        {pilotLabel ? (
          <div className="space-y-0.5">
            <p className="text-[11px] font-semibold uppercase tracking-[0.04em] text-[#7D7B75]">
              Pôle pilote
            </p>
            <p className="text-[13px] leading-relaxed text-[#1a1a1a]">{pilotLabel}</p>
          </div>
        ) : null}
        <ActionPlanExecutionDetailAssigneesSection
          execution={execution}
          currentMembershipId={currentMembershipId}
        />
        {creatorName ? (
          <div className="space-y-0.5">
            <p className="text-[11px] font-semibold uppercase tracking-[0.04em] text-[#7D7B75]">
              Créateur
            </p>
            <p className="flex min-w-0 items-center gap-2 text-[13px] leading-snug text-[#1a1a1a]">
              <span
                className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-[#E4E2DB] bg-white text-[9px] font-semibold text-[#8A857C]"
                aria-hidden
              >
                {getDisplayNameInitials(creatorName)}
              </span>
              <span className="min-w-0 break-words">{creatorLine(creatorName, execution.created_at)}</span>
            </p>
          </div>
        ) : null}
        {lifecycleLines.length > 0 ? (
          <div className="space-y-1">
            {lifecycleLines.map((line) => (
              <p key={line} className="text-[13px] italic leading-relaxed text-[#7D7B75]">
                {line}
              </p>
            ))}
          </div>
        ) : null}
      </div>
    </TerrainCard>
  )
}
