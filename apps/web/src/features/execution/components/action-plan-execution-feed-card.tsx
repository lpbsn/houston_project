import { Bell } from 'lucide-react'

import { FeedCardActionsButton, FeedCardMetaRow } from '@/components/domain/feed-card-meta-row'
import { HoustonBadge } from '@/components/ui/terrain'
import { feedCardKeyDown } from '@/lib/feed-card-keyboard'
import { getDisplayNameInitials } from '@/lib/display-names'
import {
  actionPlanFeedPendingBgClassName,
  actionPlanFeedTealBgClassName,
  terrain,
  terrainActionPlanFeedCardClassName,
  terrainFeedCardBaseClassName,
  terrainFeedInteractiveCardClassName,
} from '@/lib/terrain-styles'
import { ActionPlanPinnedBadge } from '@/features/action-plans/components/action-plan-pinned-badge'
import { ActionPlanStatusBadge } from '@/features/action-plans/components/action-plan-status-badge'
import { canOpenActionPlanExecutionFeedCardActions } from '@/features/action-plans/lib/action-plan-execution-feed-card-actions'
import type { ActionPlanExecutionFeedItem } from '@/features/action-plans/types'
import { SignalClassificationBadges } from '@/features/signals/components/signal-classification-badges'
import { formatSignalRelativeTime } from '@/features/signals/lib/signal-display'

import { ActionPlanFeedSidebar } from './action-plan-feed-sidebar'
import { ActionPlanFeedTaskProgressBar } from './action-plan-feed-task-progress-bar'
import type { ActionPlanFeedTaskProgressBarVariant } from './action-plan-feed-task-progress-bar'
import {
  actionPlanFeedSignalClassificationInput,
  formatActionPlanFeedAssigneeDisplay,
  formatActionPlanFeedMetaParts,
  getActionPlanFeedProgressState,
  getActionPlanFeedSidebarState,
  isActionPlanFeedCanceledCard,
  isActionPlanFeedDoneCard,
  isActionPlanFeedInProgressCard,
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
  showPinnedBadge?: boolean
  avatarClassName?: string
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

function ActionPlanFeedAssigneeRow({
  item,
  showStatusBadge = true,
  showPinnedBadge = showStatusBadge,
  avatarClassName = 'bg-[#EEF2FF] text-[#1B4FD8]',
}: ActionPlanFeedAssigneeRowProps) {
  const { visible, overflow } = formatActionPlanFeedAssigneeDisplay(item.assignees)
  if (visible.length === 0 && !showStatusBadge && !showPinnedBadge) {
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
            className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[10px] font-bold ${avatarClassName}`}
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
          {showPinnedBadge && item.is_pinned ? <ActionPlanPinnedBadge /> : null}
          <ActionPlanStatusBadge status={item.status} />
        </div>
      ) : showPinnedBadge && item.is_pinned ? (
        <div className="flex shrink-0 items-center">
          <ActionPlanPinnedBadge />
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
      className={terrainFeedCardBaseClassName(actionPlanFeedPendingBgClassName)}
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
        <div className="flex shrink-0 items-center gap-0.5">
          <span className="text-[11px] leading-none text-[#888]">
            {formatSignalRelativeTime(item.last_activity_at)}
          </span>
          {showActions ? (
            <ActionPlanFeedCardActionsButton item={item} onOpenActions={onOpenActions} />
          ) : null}
        </div>
      </div>

      <div className="mb-1 mt-2 flex flex-wrap items-center gap-1">
        <ActionPlanFeedHeaderBadges item={item} signalInput={signalInput} />
      </div>

      <h3 className="line-clamp-2 text-lg font-bold text-[#1a1a1a]">{item.title}</h3>

      <ActionPlanFeedMetaRow item={item} />

      <ActionPlanFeedAssigneeRow item={item} showStatusBadge={false} showPinnedBadge={false} />
    </article>
  )
}

function InProgressActionPlanFeedCard({
  item,
  onSelect,
  onOpenActions,
}: ActionPlanExecutionFeedCardProps) {
  const signalInput = actionPlanFeedSignalClassificationInput(item.signal_summary)
  const showActions =
    onOpenActions && canOpenActionPlanExecutionFeedCardActions(item.permission_hints)
  const sidebarState = getActionPlanFeedSidebarState(item.end_at)
  const progressState = getActionPlanFeedProgressState(item)

  return (
    <article
      className={terrainActionPlanFeedCardClassName()}
      onClick={() => onSelect(item.id)}
      onKeyDown={(event) => feedCardKeyDown(event, onSelect, item.id)}
      role="button"
      tabIndex={0}
    >
      <ActionPlanFeedSidebar state={sidebarState} />

      <div className="min-w-0 flex-1 p-4">
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

        {progressState ? (
          <ActionPlanFeedTaskProgressBar
            total={progressState.total}
            filled={progressState.filled}
            fractionLabel={progressState.fractionLabel}
          />
        ) : null}

        <ActionPlanFeedAssigneeRow
          item={item}
          showStatusBadge={false}
          showPinnedBadge
          avatarClassName={`${actionPlanFeedTealBgClassName} text-white`}
        />
      </div>
    </article>
  )
}

function TerminalActionPlanFeedCard({
  item,
  onSelect,
  onOpenActions,
  sidebarVariant,
  progressVariant,
  avatarClassName,
}: ActionPlanExecutionFeedCardProps & {
  sidebarVariant: 'done' | 'canceled'
  progressVariant: ActionPlanFeedTaskProgressBarVariant
  avatarClassName: string
}) {
  const signalInput = actionPlanFeedSignalClassificationInput(item.signal_summary)
  const showActions =
    onOpenActions && canOpenActionPlanExecutionFeedCardActions(item.permission_hints)
  const progressState = getActionPlanFeedProgressState(item)

  return (
    <article
      className={terrainActionPlanFeedCardClassName()}
      onClick={() => onSelect(item.id)}
      onKeyDown={(event) => feedCardKeyDown(event, onSelect, item.id)}
      role="button"
      tabIndex={0}
    >
      <ActionPlanFeedSidebar variant={sidebarVariant} />

      <div className="min-w-0 flex-1 p-4">
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

        {progressState ? (
          <ActionPlanFeedTaskProgressBar
            total={progressState.total}
            filled={progressState.filled}
            fractionLabel={progressState.fractionLabel}
            variant={progressVariant}
          />
        ) : null}

        <ActionPlanFeedAssigneeRow
          item={item}
          showStatusBadge={false}
          showPinnedBadge
          avatarClassName={avatarClassName}
        />
      </div>
    </article>
  )
}

function DoneActionPlanFeedCard(props: ActionPlanExecutionFeedCardProps) {
  return (
    <TerminalActionPlanFeedCard
      {...props}
      sidebarVariant="done"
      progressVariant="success"
      avatarClassName={`${terrain.successBg} text-white`}
    />
  )
}

function CanceledActionPlanFeedCard(props: ActionPlanExecutionFeedCardProps) {
  return (
    <TerminalActionPlanFeedCard
      {...props}
      sidebarVariant="canceled"
      progressVariant="muted"
      avatarClassName="bg-[#7D7B75] text-white"
    />
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

  if (isActionPlanFeedInProgressCard(item)) {
    return (
      <InProgressActionPlanFeedCard item={item} onSelect={onSelect} onOpenActions={onOpenActions} />
    )
  }

  if (isActionPlanFeedDoneCard(item)) {
    return <DoneActionPlanFeedCard item={item} onSelect={onSelect} onOpenActions={onOpenActions} />
  }

  if (isActionPlanFeedCanceledCard(item)) {
    return (
      <CanceledActionPlanFeedCard item={item} onSelect={onSelect} onOpenActions={onOpenActions} />
    )
  }

  return <ClassicActionPlanFeedCard item={item} onSelect={onSelect} onOpenActions={onOpenActions} />
}
