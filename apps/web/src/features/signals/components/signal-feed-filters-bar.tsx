import { useMemo, useState } from 'react'
import { RotateCcw } from 'lucide-react'
import { Popover } from 'radix-ui'

import { isDesktopWebLanding } from '@/features/auth/lib/authenticated-landing'
import { buildBusinessUnitScopeTree } from '@/features/auth/lib/business-unit-scope'
import { useBusinessUnitTreeQuery } from '@/features/auth/hooks'
import { useLgViewport } from '@/lib/lg-viewport'
import { cn } from '@/lib/utils'

import {
  buildClassificationLabelsFromTree,
} from '../lib/signal-feed-classification-selection'
import {
  EMPTY_SIGNAL_FEED_FILTERS,
  formatClassificationFilterChipLabel,
  formatClassificationFilterSummary,
  formatStatusFilterChipLabel,
  hasActiveSignalFeedFilters,
  normalizeSignalFeedFilters,
  SIGNAL_FEED_STATUS_OPTIONS,
  type SignalFeedFilters,
  type SignalFeedStatusFilter,
} from '../lib/signal-feed-filters'
import { canUseNeedsQualificationFeedFilter } from '../lib/signal-qualify-routing'
import { SignalFeedClassificationFilterSheet } from './signal-feed-classification-filter-sheet'
import { SignalFeedStatusFilterSheet } from './signal-feed-status-filter-sheet'

type SignalFeedFiltersBarProps = {
  establishmentId: string
  filters: SignalFeedFilters
  onFiltersChange: (filters: SignalFeedFilters) => void
  membershipRole?: string | null
  /** When true, render reset control inline (mobile chips row ownership). */
  showReset?: boolean
  onReset?: () => void
  /** Horizontal inset for mobile chips (safe-area aware). */
  contentClassName?: string
}

function toggleStatusFilter(
  filters: SignalFeedFilters,
  status: SignalFeedStatusFilter,
): SignalFeedFilters {
  const statuses = filters.statuses.includes(status)
    ? filters.statuses.filter((value) => value !== status)
    : [...filters.statuses, status]
  return normalizeSignalFeedFilters({ ...filters, statuses })
}

function filterChipClassName(active: boolean): string {
  return cn(
    'inline-flex h-8 shrink-0 items-center rounded-full border px-3 text-xs font-semibold whitespace-nowrap focus-visible:ring-2 focus-visible:ring-[#1B4FD8]/30 focus-visible:outline-none',
    active
      ? 'border-[#1B4FD8] bg-[#EEF4FF] text-[#1B4FD8]'
      : 'border-[#E8E6DF] bg-white text-[#5c564e]',
  )
}

export function SignalFeedFiltersBar({
  establishmentId,
  filters,
  onFiltersChange,
  membershipRole = null,
  showReset = false,
  onReset,
  contentClassName,
}: SignalFeedFiltersBarProps) {
  const isDesktopWeb = isDesktopWebLanding(useLgViewport())
  const [statusSheetOpen, setStatusSheetOpen] = useState(false)
  const [classificationSheetOpen, setClassificationSheetOpen] = useState(false)
  const [classificationPanelOpen, setClassificationPanelOpen] = useState(false)
  const normalizedFilters = normalizeSignalFeedFilters(filters)
  const filtersActive = hasActiveSignalFeedFilters(normalizedFilters)

  const treeQuery = useBusinessUnitTreeQuery(establishmentId)

  const classificationLabels = useMemo(() => {
    if (!treeQuery.data) {
      return {
        labelByBusinessUnitId: new Map<string, string>(),
        labelByActivitySubjectId: new Map<string, string>(),
      }
    }
    const businessUnits = buildBusinessUnitScopeTree(treeQuery.data).businessUnits
    return buildClassificationLabelsFromTree(businessUnits)
  }, [treeQuery.data])

  const showNeedsQualification = canUseNeedsQualificationFeedFilter(membershipRole)

  if (isDesktopWeb) {
    return (
      <div
        className="flex shrink-0 flex-wrap items-center gap-2 border-t border-[#E8E6DF] bg-white px-4 py-2"
        aria-label="Filtres des observations"
      >
        {SIGNAL_FEED_STATUS_OPTIONS.map((option) => {
          const pressed = normalizedFilters.statuses.includes(option.value)
          return (
            <button
              key={option.value}
              type="button"
              aria-pressed={pressed}
              className={cn(
                'rounded-full border px-2.5 py-1 text-xs font-semibold focus-visible:ring-2 focus-visible:ring-[#1B4FD8]/30 focus-visible:outline-none',
                pressed
                  ? 'border-[#1B4FD8] bg-[#EEF4FF] text-[#1B4FD8]'
                  : 'border-[#E8E6DF] bg-white text-[#5c564e]',
              )}
              onClick={() => onFiltersChange(toggleStatusFilter(normalizedFilters, option.value))}
            >
              {option.label}
            </button>
          )
        })}
        {showNeedsQualification ? (
          <label className="flex items-center gap-2 text-xs text-[#1a1a1a]">
            <input
              type="checkbox"
              className="h-3.5 w-3.5 rounded border-[#E8E6DF]"
              checked={normalizedFilters.needsQualification}
              onChange={(event) =>
                onFiltersChange(
                  normalizeSignalFeedFilters({
                    ...normalizedFilters,
                    needsQualification: event.target.checked,
                  }),
                )
              }
            />
            Non classifié
          </label>
        ) : null}
        <Popover.Root open={classificationPanelOpen} onOpenChange={setClassificationPanelOpen}>
          <Popover.Trigger
            type="button"
            className="rounded-full border border-[#E8E6DF] bg-white px-2.5 py-1 text-xs font-semibold text-[#1a1a1a] focus-visible:ring-2 focus-visible:ring-[#1B4FD8]/30 focus-visible:outline-none"
          >
            Pôle / Sujet
            <span className="ml-1 font-medium text-[#7D7B75]">
              {formatClassificationFilterSummary(
                normalizedFilters,
                classificationLabels.labelByBusinessUnitId,
                classificationLabels.labelByActivitySubjectId,
              )}
            </span>
          </Popover.Trigger>
          <Popover.Portal>
            <Popover.Content
              align="start"
              side="bottom"
              sideOffset={6}
              className="z-50 rounded-xl border border-[#E8E6DF] bg-white shadow-md outline-none"
            >
              {classificationPanelOpen ? (
                <SignalFeedClassificationFilterSheet
                  key={`classification-panel-${normalizedFilters.businessUnitIds.join(',')}-${normalizedFilters.activitySubjectIds.join(',')}`}
                  establishmentId={establishmentId}
                  appliedFilters={normalizedFilters}
                  surface="panel"
                  onClose={() => setClassificationPanelOpen(false)}
                  onApply={(next) => onFiltersChange(normalizeSignalFeedFilters(next))}
                />
              ) : null}
            </Popover.Content>
          </Popover.Portal>
        </Popover.Root>
      </div>
    )
  }

  const statusActive = normalizedFilters.statuses.length > 0
  const classificationActive =
    normalizedFilters.businessUnitIds.length > 0 ||
    normalizedFilters.activitySubjectIds.length > 0
  const showResetControl = showReset && filtersActive && Boolean(onReset)

  return (
    <>
      <div
        className="flex shrink-0 bg-white py-2"
        aria-label="Filtres des observations"
      >
        <div
          className={cn(
            'flex min-w-0 flex-1 items-center gap-2',
            contentClassName ?? 'px-3',
          )}
        >
          <div className="flex min-w-0 flex-1 flex-nowrap items-center gap-2 overflow-x-auto [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
            <button
              type="button"
              data-filter-kind="status"
              aria-pressed={statusActive}
              className={filterChipClassName(statusActive)}
              onClick={() => setStatusSheetOpen(true)}
            >
              {formatStatusFilterChipLabel(normalizedFilters)}
            </button>
            <button
              type="button"
              data-filter-kind="classification"
              aria-pressed={classificationActive}
              className={filterChipClassName(classificationActive)}
              onClick={() => setClassificationSheetOpen(true)}
            >
              {formatClassificationFilterChipLabel(
                normalizedFilters,
                classificationLabels.labelByBusinessUnitId,
                classificationLabels.labelByActivitySubjectId,
              )}
            </button>
            {showNeedsQualification ? (
              <button
                type="button"
                data-filter-kind="needs-qualification"
                aria-pressed={normalizedFilters.needsQualification}
                className={filterChipClassName(normalizedFilters.needsQualification)}
                onClick={() =>
                  onFiltersChange(
                    normalizeSignalFeedFilters({
                      ...normalizedFilters,
                      needsQualification: !normalizedFilters.needsQualification,
                    }),
                  )
                }
              >
                Non classifié
              </button>
            ) : null}
          </div>
          {showResetControl ? (
            <button
              type="button"
              onClick={onReset}
              aria-label="Réinitialiser les filtres"
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-[#1B4FD8] transition hover:bg-[#EEF4FF] focus-visible:ring-2 focus-visible:ring-[#1B4FD8]/30 focus-visible:outline-none"
            >
              <RotateCcw className="h-4 w-4" aria-hidden />
            </button>
          ) : null}
        </div>
      </div>

      {statusSheetOpen ? (
        <SignalFeedStatusFilterSheet
          key={`status-${normalizedFilters.statuses.join(',')}`}
          appliedFilters={normalizedFilters}
          onClose={() => setStatusSheetOpen(false)}
          onApply={(next) =>
            onFiltersChange(
              normalizeSignalFeedFilters({
                ...normalizedFilters,
                statuses: next.statuses,
              }),
            )
          }
        />
      ) : null}

      {classificationSheetOpen ? (
        <SignalFeedClassificationFilterSheet
          key={`classification-${normalizedFilters.businessUnitIds.join(',')}-${normalizedFilters.activitySubjectIds.join(',')}`}
          establishmentId={establishmentId}
          appliedFilters={normalizedFilters}
          onClose={() => setClassificationSheetOpen(false)}
          onApply={(next) => onFiltersChange(normalizeSignalFeedFilters(next))}
        />
      ) : null}
    </>
  )
}

export { EMPTY_SIGNAL_FEED_FILTERS }
