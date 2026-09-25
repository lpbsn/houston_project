import { MoreHorizontal } from 'lucide-react'
import { Popover } from 'radix-ui'

import { HoustonBadge } from '@/components/ui/terrain'
import { getDisplayNameInitials } from '@/lib/display-names'
import { cn } from '@/lib/utils'
import { ActionPlanPinnedBadge } from '@/features/action-plans/components/action-plan-pinned-badge'
import { ActionPlanStatusBadge } from '@/features/action-plans/components/action-plan-status-badge'
import {
  canOpenActionPlanExecutionFeedCardActions,
  getActionPlanExecutionFeedCardActionOptions,
  type ActionPlanExecutionFeedCardActionId,
} from '@/features/action-plans/lib/action-plan-execution-feed-card-actions'
import type { ActionPlanExecutionFeedItem } from '@/features/action-plans/types'

import {
  formatExecutionFeedCreatedLabel,
  formatExecutionFeedDelayLabel,
  formatExecutionFeedTimingLabel,
  getActionPlanFeedSidebarState,
} from '../lib/action-plan-execution-feed-card-display'
import { useFeedCardNow } from '../lib/use-feed-card-now'

type ActionPlanExecutionFeedDesktopRowProps = {
  item: ActionPlanExecutionFeedItem
  onSelect: (executionId: string) => void
  onRunAction?: (
    item: ActionPlanExecutionFeedItem,
    actionId: ActionPlanExecutionFeedCardActionId,
  ) => void
  actionsOpen?: boolean
  onActionsOpenChange?: (open: boolean) => void
  actionError?: string | null
  actionsPending?: boolean
}

function stopRowActivation(event: { stopPropagation: () => void }) {
  event.stopPropagation()
}

export function ActionPlanExecutionFeedDesktopRow({
  item,
  onSelect,
  onRunAction,
  actionsOpen = false,
  onActionsOpenChange,
  actionError = null,
  actionsPending = false,
}: ActionPlanExecutionFeedDesktopRowProps) {
  const now = useFeedCardNow()
  const showActions = Boolean(
    onRunAction && canOpenActionPlanExecutionFeedCardActions(item.permission_hints),
  )
  const actionOptions = showActions ? getActionPlanExecutionFeedCardActionOptions(item) : []
  const timingLabel = formatExecutionFeedTimingLabel(item)
  const isScheduled = item.status === 'scheduled'
  const delayLabel = formatExecutionFeedDelayLabel(
    getActionPlanFeedSidebarState(item.end_at, now, item.is_overdue, item.all_day),
  )
  const createdLabel = formatExecutionFeedCreatedLabel(item.created_at)
  const creatorName = item.created_by_display_name.trim()
  const poleLabel = item.pilot_business_unit.specific_name.trim()
  const assignees = item.assignees.filter((assignee) => assignee.display_name.trim().length > 0)

  return (
    <article className="flex flex-col gap-0 rounded-xl border border-[#E8E6DF] bg-white px-3 py-2.5">
      <div className="flex items-start gap-2">
        <button
          type="button"
          className="min-w-0 flex-1 rounded-lg px-1 text-left outline-none focus-visible:ring-2 focus-visible:ring-[#1B4FD8]/30"
          onClick={() => onSelect(item.id)}
        >
          <h3 className="break-words text-[15px] font-semibold leading-snug text-[#1a1a1a]">
            {item.title}
          </h3>
        </button>
        {showActions ? (
          <Popover.Root open={actionsOpen} onOpenChange={onActionsOpenChange}>
            <Popover.Trigger
              type="button"
              aria-label="Actions du plan d’action"
              className={cn(
                'flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-[#5F5A52]',
                'hover:bg-[#F5F4F0] focus-visible:ring-2 focus-visible:ring-[#1B4FD8]/30 focus-visible:outline-none',
              )}
              onClick={stopRowActivation}
            >
              <MoreHorizontal className="h-4 w-4" aria-hidden />
            </Popover.Trigger>
            <Popover.Portal>
              <Popover.Content
                align="end"
                side="bottom"
                sideOffset={6}
                className="z-50 w-56 rounded-xl border border-[#E8E6DF] bg-white p-1 shadow-md outline-none"
                onClick={stopRowActivation}
              >
                <div role="menu" aria-label="Actions du plan d’action">
                  {actionOptions.map((option) => (
                    <button
                      key={option.id}
                      type="button"
                      role="menuitem"
                      className="flex w-full rounded-lg px-3 py-2 text-left text-sm font-medium text-[#1a1a1a] hover:bg-[#F5F4F0] focus-visible:ring-2 focus-visible:ring-[#1B4FD8]/30 focus-visible:outline-none disabled:opacity-50"
                      disabled={actionsPending}
                      onClick={(event) => {
                        stopRowActivation(event)
                        onRunAction?.(item, option.id)
                      }}
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
                {actionError ? (
                  <p className="px-3 py-2 text-sm text-destructive" role="alert">
                    {actionError}
                  </p>
                ) : null}
              </Popover.Content>
            </Popover.Portal>
          </Popover.Root>
        ) : null}
      </div>
      <button
        type="button"
        className="flex flex-col gap-2 rounded-lg px-1 py-0.5 text-left outline-none focus-visible:ring-2 focus-visible:ring-[#1B4FD8]/30"
        onClick={() => onSelect(item.id)}
      >
        <span className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
          <span className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
            {item.is_pinned ? <ActionPlanPinnedBadge /> : null}
            <ActionPlanStatusBadge status={item.status} validatedAt={item.validated_at} />
            {poleLabel ? (
              <HoustonBadge variant="gray" className="max-w-full leading-none break-words">
                {poleLabel}
              </HoustonBadge>
            ) : null}
          </span>
          {timingLabel ? (
            <span
              className={cn(
                'max-w-full break-words text-right text-[12px] leading-snug',
                isScheduled ? 'font-semibold text-[#8B6914]' : 'text-[#5c564e]',
              )}
            >
              {timingLabel}
            </span>
          ) : null}
        </span>
        {assignees.length > 0 || delayLabel ? (
          <span className="flex flex-wrap items-start justify-between gap-x-3 gap-y-1">
            {assignees.length > 0 ? (
              <span className="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1">
                {assignees.map((assignee) => (
                  <span
                    key={assignee.membership_id}
                    className="inline-flex max-w-full items-center gap-1.5"
                  >
                    <span
                      className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[#EEF2FF] text-[10px] font-bold text-[#1B4FD8]"
                      aria-hidden
                    >
                      {getDisplayNameInitials(assignee.display_name)}
                    </span>
                    <span className="break-words text-[12px] leading-snug text-[#5c564e]">
                      {assignee.display_name}
                    </span>
                  </span>
                ))}
              </span>
            ) : (
              <span />
            )}
            {delayLabel ? (
              <span className="shrink-0 text-[12px] font-semibold leading-snug text-[#E24B4A]">
                {delayLabel}
              </span>
            ) : null}
          </span>
        ) : null}
        {createdLabel ? (
          <span className="flex flex-wrap items-center gap-x-1.5 gap-y-1 text-[11px] leading-snug text-[#9a958c]">
            <span>{createdLabel}</span>
            {creatorName ? (
              <>
                <span>par</span>
                <span className="inline-flex max-w-full items-center gap-1.5">
                  <span
                    className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[#F0EFE9] text-[9px] font-bold text-[#5c564e]"
                    aria-hidden
                  >
                    {getDisplayNameInitials(creatorName)}
                  </span>
                  <span className="break-words">{creatorName}</span>
                </span>
              </>
            ) : null}
          </span>
        ) : null}
      </button>
    </article>
  )
}
