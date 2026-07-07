import { Bell } from 'lucide-react'

import { FeedCardActionsButton, FeedCardMetaRow } from '@/components/domain/feed-card-meta-row'
import { HoustonBadge } from '@/components/ui/terrain'
import { feedCardKeyDown } from '@/lib/feed-card-keyboard'
import {
  terrainFeedCardBaseClassName,
  terrainFeedInteractiveCardClassName,
} from '@/lib/terrain-styles'
import { getDisplayNameInitials } from '@/lib/display-names'
import { ActionPlanPinnedBadge } from '@/features/action-plans/components/action-plan-pinned-badge'
import { ActionPlanStatusBadge } from '@/features/action-plans/components/action-plan-status-badge'
import { canOpenActionPlanExecutionFeedCardActions } from '@/features/action-plans/lib/action-plan-execution-feed-card-actions'
import type { ActionPlanExecutionFeedItem } from '@/features/action-plans/types'
import { SignalClassificationBadges } from '@/features/signals/components/signal-classification-badges'
import { formatSignalRelativeTime } from '@/features/signals/lib/signal-display'

import {
  actionPlanFeedSignalClassificationInput,
  formatActionPlanFeedAssigneeDisplay,
  formatActionPlanFeedMetaParts,
  isActionPlanFeedPendingValidationCard,
} from '../lib/action-plan-execution-feed-card-display'

type ActionPlanExecutionFeedCardProps = {
  item: ActionPlanExecutionFeedItem
  onSelect: (executionId: string) => void
  onOpenActions?: (item: ActionPlanExecutionFeedItem) => void
}

type ActionPlanFeedAssigneeRowProps = {
  item: ActionPlanExecutionFeedItem
  showStatusBadge?: boolean
}

function stopCardNavigation(event: { stopPropagation: () => void }) {
  event.stopPropagation()
}

type ActionPlanFeedCardActionsButtonProps = {
  item: ActionPlanExecutionFeedItem
  onOpenActions: (item: ActionPlanExecutionFeedItem) => void
}

function ActionPlanFeedCardActionsButton({ item, onOpenActions }: ActionPlanFeedCardActionsButtonProps) {
  return (
    <FeedCardActionsButton
      ariaLabel="Actions du plan d’action"
      onClick={(event) => {
        stopCardNavigation(event)
        onOpenActions(item)
      }}
    />
  )
}

function ActionPlanFeedPilotBadge({ label }: { label: string }) {
  return <HoustonBadge variant="gray">{label}</HoustonBadge>
}

type ActionPlanFeedHeaderBadgesProps = {
  item: ActionPlanExecutionFeedItem
  signalInput: ReturnType<typeof actionPlanFeedSignalClassificationInput>
}

function ActionPlanFeedHeaderBadges({ item, signalInput }: ActionPlanFeedHeaderBadgesProps) {
  return (
    <>
      <ActionPlanFeedPilotBadge label={item.pilot_business_unit.label} />
      {signalInput ? <SignalClassificationBadges signal={signalInput} /> : null}
    </>
  )
}

type ActionPlanFeedCardHeaderProps = {
  item: ActionPlanExecutionFeedItem
  signalInput: ReturnType<typeof actionPlanFeedSignalClassificationInput>
  showActions: boolean
  onOpenActions?: (item: ActionPlanExecutionFeedItem) => void
}

function ActionPlanFeedCardHeader({
  item,
  signalInput,
  showActions,
  onOpenActions,
}: ActionPlanFeedCardHeaderProps) {
  return (
    <>
      <FeedCardMetaRow
        timeLabel={formatSignalRelativeTime(item.last_activity_at)}
        badges={<ActionPlanFeedHeaderBadges item={item} signalInput={signalInput} />}
        actions={
          showActions && onOpenActions ? (
            <ActionPlanFeedCardActionsButton item={item} onOpenActions={onOpenActions} />
          ) : null
        }
      />
      <h3 className="line-clamp-2 text-lg font-bold text-[#1a1a1a]">{item.title}</h3>
    </>
  )
}

function ActionPlanFeedMetaRow({ item }: { item: ActionPlanExecutionFeedItem }) {
  const { deadlineLabel, taskProgressLabel } = formatActionPlanFeedMetaParts(item)

  if (!deadlineLabel && !taskProgressLabel) {
    return null
  }

  return (
    <div className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] text-[#888]">
      {deadlineLabel ? (
        <span className={item.is_overdue ? 'font-medium text-[#E24B4A]' : undefined}>
          {deadlineLabel}
        </span>
      ) : null}
      {deadlineLabel && taskProgressLabel ? <span aria-hidden> - </span> : null}
      {taskProgressLabel ? (
        <span className="font-medium tabular-nums text-[#555]">{taskProgressLabel}</span>
      ) : null}
    </div>
  )
}

function ActionPlanFeedAssigneeRow({ item, showStatusBadge = true }: ActionPlanFeedAssigneeRowProps) {
  const { visible, overflow } = formatActionPlanFeedAssigneeDisplay(item.assignees)
  if (visible.length === 0 && !showStatusBadge) {
    return null
  }

  const primaryInitials = getDisplayNameInitials(visible[0] ?? '')
  const assigneeLabel =
    overflow > 0 ? `${visible.join(', ')} +${overflow}` : visible.join(', ')

  return (
    <div className="mt-3 flex items-center justify-between gap-3 border-t border-[#F0EFE9] pt-3">
      {visible.length > 0 ? (
        <div className="flex min-w-0 items-center gap-2">
          <div
            className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[#EEF2FF] text-[10px] font-bold text-[#1B4FD8]"
            aria-hidden
          >
            {primaryInitials}
          </div>
          <span className="truncate text-[11px] text-[#888]">{assigneeLabel}</span>
        </div>
      ) : (
        <span />
      )}
      {showStatusBadge ? (
        <div className="flex shrink-0 items-center gap-1.5">
          {item.is_pinned ? <ActionPlanPinnedBadge /> : null}
          <ActionPlanStatusBadge status={item.status} />
        </div>
      ) : null}
    </div>
  )
}

function PendingValidationActionPlanFeedCard({
  item,
  onSelect,
  onOpenActions,
}: ActionPlanExecutionFeedCardProps) {
  const signalInput = actionPlanFeedSignalClassificationInput(item.signal_summary)
  const showActions =
    onOpenActions && canOpenActionPlanExecutionFeedCardActions(item.permission_hints)

  return (
    <article
      className={terrainFeedCardBaseClassName(
        'border border-[#E69138] bg-[#FFF9ED] hover:border-[#E69138]/80',
      )}
      onClick={() => onSelect(item.id)}
      onKeyDown={(event) => feedCardKeyDown(event, onSelect, item.id)}
      role="button"
      tabIndex={0}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex min-w-0 items-center gap-1.5">
          <Bell className="h-4 w-4 shrink-0 text-[#E69138]" aria-hidden />
          <span className="truncate text-[13px] font-bold text-[#B45309]">
            En attente de validation
          </span>
        </div>
        {showActions ? (
          <ActionPlanFeedCardActionsButton item={item} onOpenActions={onOpenActions} />
        ) : null}
      </div>

      <div className="my-2 border-t border-[#F0DFC8]" />

      <ActionPlanFeedCardHeader
        item={item}
        signalInput={signalInput}
        showActions={Boolean(showActions)}
        onOpenActions={onOpenActions}
      />

      <ActionPlanFeedMetaRow item={item} />

      <ActionPlanFeedAssigneeRow item={item} showStatusBadge={false} />
    </article>
  )
}

function ClassicActionPlanFeedCard({
  item,
  onSelect,
  onOpenActions,
}: ActionPlanExecutionFeedCardProps) {
  const signalInput = actionPlanFeedSignalClassificationInput(item.signal_summary)
  const showActions =
    onOpenActions && canOpenActionPlanExecutionFeedCardActions(item.permission_hints)

  return (
    <article
      className={terrainFeedInteractiveCardClassName()}
      style={{ borderLeftColor: '#1B4FD8' }}
      onClick={() => onSelect(item.id)}
      onKeyDown={(event) => feedCardKeyDown(event, onSelect, item.id)}
      role="button"
      tabIndex={0}
    >
      <ActionPlanFeedCardHeader
        item={item}
        signalInput={signalInput}
        showActions={Boolean(showActions)}
        onOpenActions={onOpenActions}
      />

      <ActionPlanFeedMetaRow item={item} />

      <ActionPlanFeedAssigneeRow item={item} />
    </article>
  )
}

export function ActionPlanExecutionFeedCard({
  item,
  onSelect,
  onOpenActions,
}: ActionPlanExecutionFeedCardProps) {
  if (isActionPlanFeedPendingValidationCard(item)) {
    return (
      <PendingValidationActionPlanFeedCard
        item={item}
        onSelect={onSelect}
        onOpenActions={onOpenActions}
      />
    )
  }

  return <ClassicActionPlanFeedCard item={item} onSelect={onSelect} onOpenActions={onOpenActions} />
}
