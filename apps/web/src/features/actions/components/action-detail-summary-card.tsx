import { HoustonBadge, TerrainCard } from '@/components/ui/terrain'

import type { ActionDetail } from '../types'
import { ActionStatusBadge } from './action-status-badge'
import {
  formatActionCreatorFooterLabel,
  getActionDomainBadgeLabel,
  getActionLocationText,
  getDisplayNameInitials,
  shouldShowActionUrgentBadge,
} from '../lib/action-display'

type ActionDetailSummaryCardProps = {
  action: ActionDetail
  onNavigate: (pathname: string) => void
}

export function ActionDetailSummaryCard({ action, onNavigate }: ActionDetailSummaryCardProps) {
  const showUrgentBadge = shouldShowActionUrgentBadge(action.signal_summary)
  const domainLabel = getActionDomainBadgeLabel(action.domain_key)
  const locationText = getActionLocationText(action.signal_summary)
  const assigneeInitials = getDisplayNameInitials(action.assigned_to_display_name)
  const creatorLabel = formatActionCreatorFooterLabel(action.created_by_display_name)

  return (
    <TerrainCard>
      <div className="flex items-start justify-between gap-3">
        <h2 className="min-w-0 flex-1 text-[17px] font-semibold leading-snug text-[#1a1a1a]">
          {action.title}
        </h2>
        <div className="flex shrink-0 flex-col items-center gap-1">
          <div
            className="flex h-9 w-9 items-center justify-center rounded-full bg-[#EEF2FF] text-[11px] font-bold text-[#1B4FD8]"
            aria-hidden
          >
            {assigneeInitials}
          </div>
          <span className="max-w-[72px] truncate text-center text-[10px] text-[#888]">
            {action.assigned_to_display_name}
          </span>
        </div>
      </div>

      {action.signal_summary ? (
        <button
          type="button"
          className="mt-1 block w-full text-left text-[11px] text-[#aaa] hover:text-[#888]"
          onClick={() => onNavigate(`/signals/${action.signal_summary!.id}`)}
        >
          Signal lié · {action.signal_summary.title}
        </button>
      ) : null}

      <p className="mt-1.5 text-[11px] text-[#aaa]">{creatorLabel}</p>

      <div className="mt-2 flex flex-wrap gap-1">
        {showUrgentBadge ? <HoustonBadge variant="red">URGENT</HoustonBadge> : null}
        {domainLabel ? <HoustonBadge variant="gray">{domainLabel}</HoustonBadge> : null}
        <ActionStatusBadge status={action.status} labelVariant="feed" />
      </div>

      {locationText ? (
        <p className="mt-2 text-[12px] text-[#888]">
          <span className="text-[#E24B4A]" aria-hidden>
            📍{' '}
          </span>
          {locationText}
        </p>
      ) : null}
    </TerrainCard>
  )
}
