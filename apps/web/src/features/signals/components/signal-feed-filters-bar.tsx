import { useMemo, useState } from 'react'
import { Popover } from 'radix-ui'

import { TerrainFilterSlot } from '@/components/ui/terrain'
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
  formatClassificationFilterSummary,
  formatStatusFilterSummary,
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

export function SignalFeedFiltersBar({
  establishmentId,
  filters,
  onFiltersChange,
  membershipRole = null,
}: SignalFeedFiltersBarProps) {
  const isDesktopWeb = isDesktopWebLanding(useLgViewport())
  const [statusSheetOpen, setStatusSheetOpen] = useState(false)
  const [classificationSheetOpen, setClassificationSheetOpen] = useState(false)
  const [classificationPanelOpen, setClassificationPanelOpen] = useState(false)
  const normalizedFilters = normalizeSignalFeedFilters(filters)

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

  return (
    <>
      <div
        className="flex shrink-0 flex-col gap-2 border-t border-[#E8E6DF] bg-white px-3 py-2 pb-3"
        aria-label="Filtres des observations"
      >
        <div className="flex gap-2">
          <div className="flex flex-1" data-filter-kind="status">
            <TerrainFilterSlot
              label="Statut"
              value={formatStatusFilterSummary(normalizedFilters)}
              disabled={false}
              onClick={() => setStatusSheetOpen(true)}
            />
          </div>
          <div className="flex flex-1" data-filter-kind="classification">
            <TerrainFilterSlot
              label="Pôle / Sujet"
              value={formatClassificationFilterSummary(
                normalizedFilters,
                classificationLabels.labelByBusinessUnitId,
                classificationLabels.labelByActivitySubjectId,
              )}
              disabled={false}
              onClick={() => setClassificationSheetOpen(true)}
            />
          </div>
        </div>
        {showNeedsQualification ? (
          <label className="flex min-h-10 items-center gap-2 text-[13px] text-[#1a1a1a]">
            <input
              type="checkbox"
              className="h-4 w-4 rounded border-[#E8E6DF]"
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
