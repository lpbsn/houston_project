import type { ReactNode } from 'react'
import { Bell } from 'lucide-react'

import { FeedCardActionsButton, FeedCardMetaRow } from '@/components/domain/feed-card-meta-row'
import { HoustonBadge } from '@/components/ui/terrain'
import { feedCardKeyDown } from '@/lib/feed-card-keyboard'
import { getDisplayNameInitials } from '@/lib/display-names'
import {
  actionPlanFeedPendingBgClassName,
  actionPlanFeedScheduledBgClassName,
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
import { formatSignalRelativeTime } from '@/features/signals/lib/signal-display'
import { formatSignalClassification } from '@/lib/signal-classification'

import { ActionPlanFeedSidebar } from './action-plan-feed-sidebar'
import { ActionPlanFeedTaskProgressBar } from './action-plan-feed-task-progress-bar'
import type { ActionPlanFeedTaskProgressBarVariant } from './action-plan-feed-task-progress-bar'
import {
  actionPlanFeedSignalClassificationInput,
  formatActionPlanFeedAssigneeDisplay,
  formatActionPlanFeedMetaParts,
  getActionPlanFeedProgressState,
  getActionPlanFeedSidebarState,
  getActionPlanFeedStartCountdownState,
  isActionPlanFeedCanceledCard,
  isActionPlanFeedDoneCard,
  isActionPlanFeedInProgressCard,
  isActionPlanFeedPendingValidationCard,
  isActionPlanFeedScheduledCard,
} from '../lib/action-plan-execution-feed-card-display'
import { useFeedCardNow } from '../lib/use-feed-card-now'

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

type ActionPlanFeedClassificationBlockProps = {
  item: ActionPlanExecutionFeedItem
  signalInput: ReturnType<typeof actionPlanFeedSignalClassificationInput>
  children: (badges: ReactNode) => ReactNode
}

/** Flat pilot + primary badges; `Concerné` is rendered below the badges row (not inside it). */
function ActionPlanFeedClassificationBlock({
  item,
  signalInput,
  children,
}: ActionPlanFeedClassificationBlockProps) {
  const classification = signalInput ? formatSignalClassification(signalInput) : null
  const badges = (
    <>
      <HoustonBadge variant="gray" className="shrink-0 leading-none">
        {item.pilot_business_unit.specific_name}
      </HoustonBadge>
      {classification?.primaryLine ? (
        <HoustonBadge variant="gray" className="min-w-0 truncate leading-none">
          {classification.primaryLine}
        </HoustonBadge>
      ) : null}
    </>
  )

  return (
    <>
      {children(badges)}
      {classification?.affectedLine ? (
        <p className="mb-1 text-[11px] leading-none text-[#888]">{classification.affectedLine}</p>
      ) : null}
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
      <ActionPlanFeedClassificationBlock item={item} signalInput={signalInput}>
        {(badges) => (
          <FeedCardMetaRow
            timeLabel={formatSignalRelativeTime(item.last_activity_at)}
            badges={badges}
            actions={
              showActions && onOpenActions ? (
                <ActionPlanFeedCardActionsButton item={item} onOpenActions={onOpenActions} />
              ) : null
            }
          />
        )}
      </ActionPlanFeedClassificationBlock>
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
          <ActionPlanStatusBadge status={item.status} validatedAt={item.validated_at} />
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

      <ActionPlanFeedClassificationBlock item={item} signalInput={signalInput}>
        {(badges) => (
          <div className="mb-1 mt-2 flex flex-wrap items-center gap-1">{badges}</div>
        )}
      </ActionPlanFeedClassificationBlock>

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
  const now = useFeedCardNow()
  const sidebarState = getActionPlanFeedSidebarState(item.end_at, now, item.is_overdue)
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
        <ActionPlanFeedClassificationBlock item={item} signalInput={signalInput}>
          {(badges) => (
            <FeedCardMetaRow
              timeLabel={formatSignalRelativeTime(item.last_activity_at)}
              badges={badges}
              actions={
                showActions && onOpenActions ? (
                  <ActionPlanFeedCardActionsButton item={item} onOpenActions={onOpenActions} />
                ) : null
              }
            />
          )}
        </ActionPlanFeedClassificationBlock>

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

function ScheduledActionPlanFeedCardHeader({
  item,
  signalInput,
  showActions,
  onOpenActions,
}: ActionPlanFeedCardHeaderProps) {
  return (
    <ActionPlanFeedClassificationBlock item={item} signalInput={signalInput}>
      {(badges) => (
        <div className="mb-1 flex items-center justify-between gap-2">
          <div className="flex min-w-0 items-center gap-1">{badges}</div>
          <div className="flex shrink-0 items-center gap-0.5">
            <span className="text-[11px] leading-none text-[#888]">
              {formatSignalRelativeTime(item.last_activity_at)}
            </span>
            {showActions && onOpenActions ? (
              <ActionPlanFeedCardActionsButton item={item} onOpenActions={onOpenActions} />
            ) : null}
          </div>
        </div>
      )}
    </ActionPlanFeedClassificationBlock>
  )
}

function ScheduledActionPlanFeedCard({
  item,
  onSelect,
  onOpenActions,
}: ActionPlanExecutionFeedCardProps) {
  const signalInput = actionPlanFeedSignalClassificationInput(item.signal_summary)
  const showActions =
    onOpenActions && canOpenActionPlanExecutionFeedCardActions(item.permission_hints)
  const now = useFeedCardNow()
  const sidebarState = getActionPlanFeedStartCountdownState(item.start_at, now)

  return (
    <article
      className={terrainActionPlanFeedCardClassName('hover:border-[#8B6914]/30')}
      onClick={() => onSelect(item.id)}
      onKeyDown={(event) => feedCardKeyDown(event, onSelect, item.id)}
      role="button"
      tabIndex={0}
    >
      <ActionPlanFeedSidebar state={sidebarState} />

      <div className="min-w-0 flex-1 p-4">
        <ScheduledActionPlanFeedCardHeader
          item={item}
          signalInput={signalInput}
          showActions={Boolean(showActions)}
          onOpenActions={onOpenActions}
        />

        <h3 className="line-clamp-2 text-lg font-bold text-[#1a1a1a]">{item.title}</h3>

        <ActionPlanFeedAssigneeRow
          item={item}
          showStatusBadge
          showPinnedBadge={false}
          avatarClassName={`${actionPlanFeedScheduledBgClassName} text-white`}
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
        <ActionPlanFeedClassificationBlock item={item} signalInput={signalInput}>
          {(badges) => (
            <FeedCardMetaRow
              timeLabel={formatSignalRelativeTime(item.last_activity_at)}
              badges={badges}
              actions={
                showActions && onOpenActions ? (
                  <ActionPlanFeedCardActionsButton item={item} onOpenActions={onOpenActions} />
                ) : null
              }
            />
          )}
        </ActionPlanFeedClassificationBlock>

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

  if (isActionPlanFeedScheduledCard(item)) {
    return (
      <ScheduledActionPlanFeedCard item={item} onSelect={onSelect} onOpenActions={onOpenActions} />
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
