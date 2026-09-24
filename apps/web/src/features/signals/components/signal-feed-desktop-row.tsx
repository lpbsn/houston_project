import { MapPin, MoreHorizontal, Pin } from 'lucide-react'
import { Popover } from 'radix-ui'

import { getDisplayNameInitials } from '@/lib/display-names'
import { formatSignalClassification } from '@/lib/signal-classification'
import { terrainFeedAvatar } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

import {
  formatSignalRelativeTime,
  formatSignalAggregationBadge,
  formatSignalAggregationLabel,
  PINNED_SIGNAL_CARD_BANNER_LABEL,
} from '../lib/signal-display'
import {
  canOpenSignalFeedCardActions,
  getSignalFeedCardActionOptions,
  type SignalFeedCardActionId,
} from '../lib/signal-feed-card-actions'
import { isSignalMissingResponsibleClassification } from '../lib/signal-unclassified'
import type { SignalFeedItem } from '../types'
import type { SignalFeedQuickActionResult } from '../hooks/use-signal-feed-quick-actions'
import { SignalClassificationBadges } from './signal-classification-badges'
import { SignalStatusBadge } from './signal-status-badge'
import { SignalUnclassifiedBadge } from './signal-unclassified-badge'

type SignalFeedDesktopRowProps = {
  item: SignalFeedItem
  onSelect: (signalId: string) => void
  onRunAction?: (item: SignalFeedItem, actionId: SignalFeedCardActionId) => SignalFeedQuickActionResult
  actionsOpen?: boolean
  onActionsOpenChange?: (open: boolean) => void
  showEstablishment?: boolean
  pinned?: boolean
  actionsPending?: boolean
  actionError?: string | null
}

function stopRowActivation(event: { stopPropagation: () => void }) {
  event.stopPropagation()
}

const metaTextClassName = 'max-w-full break-words text-[12px] leading-snug text-[#5c564e]'
const lineClassName =
  'flex w-full min-w-0 flex-wrap items-center justify-start gap-x-2 gap-y-1 [&>*]:min-w-0 [&>*]:max-w-full'

export function SignalFeedDesktopRow({
  item,
  onSelect,
  onRunAction,
  actionsOpen = false,
  onActionsOpenChange,
  showEstablishment = false,
  pinned = false,
  actionsPending = false,
  actionError = null,
}: SignalFeedDesktopRowProps) {
  const reporterName = item.reporter_display_name?.trim() ?? ''
  const reporterInitials = reporterName ? getDisplayNameInitials(reporterName) : null
  const showActions = Boolean(
    onRunAction && canOpenSignalFeedCardActions(item.permission_hints),
  )
  const actionOptions = showActions ? getSignalFeedCardActionOptions(item) : []
  const classification = formatSignalClassification(item)
  const affectedLabel = classification.affectedLine ? classification.affectedLabel : null
  const location = item.location_text.trim()
  const establishmentName = item.establishment_name?.trim() ?? ''

  return (
    <article className="flex flex-col gap-1.5 rounded-xl border border-[#E8E6DF] bg-white px-3 py-2">
      {pinned ? (
        <span className="flex items-center gap-1 px-1 text-[11px] font-semibold text-[#7D7B75]">
          <Pin className="h-3 w-3" aria-hidden />
          {PINNED_SIGNAL_CARD_BANNER_LABEL}
        </span>
      ) : null}
      <div className="flex items-center gap-1">
        <button
          type="button"
          className="min-w-0 flex-1 rounded-lg px-1 py-0.5 text-left outline-none focus-visible:ring-2 focus-visible:ring-[#1B4FD8]/30"
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
              aria-label="Actions de l'observation"
              className={cn(
                'flex h-8 w-8 items-center justify-center rounded-md text-[#5F5A52]',
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
                className="z-50 w-64 rounded-xl border border-[#E8E6DF] bg-white p-1 shadow-md outline-none"
                onClick={stopRowActivation}
              >
                <div role="menu" aria-label="Actions de l'observation">
                  {actionOptions.map((option) => (
                    <button
                      key={option.id}
                      type="button"
                      role="menuitem"
                      className="flex w-full rounded-lg px-3 py-2 text-left text-sm font-medium text-[#1a1a1a] hover:bg-[#F5F4F0] focus-visible:ring-2 focus-visible:ring-[#1B4FD8]/30 focus-visible:outline-none disabled:opacity-50"
                      disabled={actionsPending}
                      onClick={(event) => {
                        stopRowActivation(event)
                        const result = onRunAction?.(item, option.id)
                        if (result === 'close') {
                          onActionsOpenChange?.(false)
                        }
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
        className="-mt-2.5 grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-1 gap-y-1.5 rounded-lg py-0.5 text-left outline-none focus-visible:ring-2 focus-visible:ring-[#1B4FD8]/30"
        onClick={() => onSelect(item.id)}
      >
        <span className={cn(lineClassName, 'col-start-1 px-1')}>
          <SignalStatusBadge status={item.status} variant="feed" />
          <SignalClassificationBadges
            signal={item}
            hideAffectedLine
            wrapLabel
            leading={
              isSignalMissingResponsibleClassification(item) ? (
                <SignalUnclassifiedBadge signal={item} variant="feed" />
              ) : undefined
            }
          />
        </span>
        <span className={cn(lineClassName, 'col-start-1 px-1')}>
          {reporterName ? (
            <span className="inline-flex max-w-full items-center gap-1.5">
              <span
                className={cn(
                  'flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[10px] font-bold',
                  terrainFeedAvatar,
                )}
                aria-hidden
              >
                {reporterInitials}
              </span>
              <span className={metaTextClassName}>{reporterName}</span>
            </span>
          ) : null}
          {location ? (
            <span className="inline-flex max-w-full items-start gap-1 text-[12px] leading-snug text-[#888]">
              <MapPin className="mt-0.5 h-3 w-3 shrink-0" aria-hidden />
              <span className="min-w-0 break-words">{location}</span>
            </span>
          ) : null}
          {affectedLabel ? (
            <span className={metaTextClassName}>{`Pôle concerné : ${affectedLabel}`}</span>
          ) : null}
          {showEstablishment && establishmentName ? (
            <span className={cn(metaTextClassName, 'font-medium')}>{establishmentName}</span>
          ) : null}
          {item.resolution_request?.status === 'pending' ? (
            <span className="max-w-full break-words rounded-full bg-[#EEF4FF] px-2 py-0.5 text-[10px] font-semibold leading-snug text-[#355CA8]">
              Validation demandée
            </span>
          ) : null}
        </span>
        <span className="col-start-2 row-start-2 flex items-center justify-end gap-2 self-center">
          <time
            className="whitespace-nowrap text-[12px] leading-snug text-[#888]"
            dateTime={item.last_activity_at}
          >
            {formatSignalRelativeTime(item.last_activity_at)}
          </time>
          {item.aggregation_count > 0 ? (
            <span
              className="inline-flex rounded-full bg-[#1B4FD8] px-1.5 py-0.5 text-[10px] font-bold text-white tabular-nums"
              aria-label={formatSignalAggregationLabel(item.aggregation_count)}
            >
              {formatSignalAggregationBadge(item.aggregation_count)}
            </span>
          ) : null}
        </span>
      </button>
    </article>
  )
}
