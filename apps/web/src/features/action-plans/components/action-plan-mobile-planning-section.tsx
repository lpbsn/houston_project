import { ChevronRight } from 'lucide-react'
import { useEffect, useRef, type ReactNode } from 'react'

import { TerrainCard, TerrainSectionLabel } from '@/components/ui/terrain'
import { cn } from '@/lib/utils'

import {
  formatDateTimeSummary,
  formatRecurrenceDaysSummary,
  hasGlobalRepeat,
  isAllDayPlanningDraft,
  type ActionPlanEventPlanningDraft,
} from '../lib/action-plan-event-planning-form'
import type { ActionPlanLaunchTiming } from './action-plan-launch-planning'

export type ActionPlanMobilePlanningSummaryTiming = ActionPlanLaunchTiming | 'locked'

type ActionPlanMobilePlanningSectionProps = {
  draft: ActionPlanEventPlanningDraft
  timing: ActionPlanMobilePlanningSummaryTiming
  open: boolean
  onOpenChange: (open: boolean) => void
  expandNonce: number
  shouldExpand: boolean
  onReveal?: () => void
  children: ReactNode
}

export function formatMobilePlanningWhenSummary(
  draft: ActionPlanEventPlanningDraft,
  timing: ActionPlanMobilePlanningSummaryTiming,
): string {
  if (timing === 'now' && !draft.usePerAssigneeChronology) {
    return 'Maintenant'
  }
  if (draft.usePerAssigneeChronology) {
    return 'Par assigné'
  }
  if (!draft.startDate.trim()) {
    return 'Non défini'
  }
  const start = formatDateTimeSummary(
    draft.startDate,
    isAllDayPlanningDraft(draft) ? '' : draft.startTime,
  )
  const endDate = hasGlobalRepeat(draft) ? '' : draft.endDate
  if (!endDate.trim()) {
    return start
  }
  const end = formatDateTimeSummary(endDate, isAllDayPlanningDraft(draft) ? '' : draft.endTime)
  return `${start} → ${end}`
}

export function formatMobilePlanningRecurrenceSummary(
  draft: ActionPlanEventPlanningDraft,
  timing: ActionPlanMobilePlanningSummaryTiming,
): string | null {
  if (timing === 'now' || !draft.repeatEnabled || draft.usePerAssigneeChronology) {
    return null
  }
  return formatRecurrenceDaysSummary(draft.recurrenceDays)
}

export function ActionPlanAssigneeSummaryRow({
  summary,
  editable,
  error,
  onOpen,
}: {
  summary: string
  editable: boolean
  error?: string
  onOpen: () => void
}) {
  return (
    <div className="border-b border-[#E8E6DF] last:border-b-0" data-action-plan-field="assignees">
      {editable ? (
        <button
          type="button"
          className="flex w-full items-center justify-between gap-3 px-3 py-3 text-left active:bg-[#F5F4F0]"
          onClick={onOpen}
        >
          <span className="text-sm text-[#1a1a1a]">Assignés</span>
          <span className="flex min-w-0 items-center gap-1.5 text-sm text-[#7D7B75]">
            <span className="truncate">{summary}</span>
            <ChevronRight className="size-4 shrink-0" aria-hidden />
          </span>
        </button>
      ) : (
        <div className="flex items-center justify-between gap-3 px-3 py-3">
          <span className="text-sm text-[#1a1a1a]">Assignés</span>
          <span className="truncate text-sm text-[#7D7B75]">{summary}</span>
        </div>
      )}
      {error ? <p className="px-3 pb-2 text-xs text-destructive">{error}</p> : null}
    </div>
  )
}

export function ActionPlanMobilePlanningSection({
  draft,
  timing,
  open,
  onOpenChange,
  expandNonce,
  shouldExpand,
  onReveal,
  children,
}: ActionPlanMobilePlanningSectionProps) {
  const lastExpandNonceRef = useRef(0)
  const whenSummary = formatMobilePlanningWhenSummary(draft, timing)
  const recurrenceSummary = formatMobilePlanningRecurrenceSummary(draft, timing)

  useEffect(() => {
    if (expandNonce > lastExpandNonceRef.current && shouldExpand) {
      lastExpandNonceRef.current = expandNonce
      onOpenChange(true)
      onReveal?.()
    }
  }, [expandNonce, onOpenChange, onReveal, shouldExpand])

  return (
    <section className="space-y-2" data-testid="action-plan-mobile-planning">
      <TerrainSectionLabel>Planification</TerrainSectionLabel>
      <TerrainCard className="overflow-hidden p-0">
        <button
          type="button"
          className="flex w-full items-center justify-between gap-3 px-3 py-3 text-left active:bg-[#F5F4F0]"
          aria-expanded={open}
          onClick={() => onOpenChange(!open)}
        >
          <span className="text-sm text-[#1a1a1a]">Quand</span>
          <span className="flex min-w-0 items-center gap-1.5 text-sm text-[#7D7B75]">
            <span className="truncate">{whenSummary}</span>
            <ChevronRight
              className={cn('size-4 shrink-0 transition-transform', open && 'rotate-90')}
              aria-hidden
            />
          </span>
        </button>
        {recurrenceSummary ? (
          <div className="flex items-center justify-between gap-3 border-t border-[#E8E6DF] px-3 py-3">
            <span className="text-sm text-[#1a1a1a]">Répétition</span>
            <span className="truncate text-sm text-[#7D7B75]">{recurrenceSummary}</span>
          </div>
        ) : null}
      </TerrainCard>
      {open ? children : null}
    </section>
  )
}
