import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'

import { TerrainFilterSlot } from '@/components/ui/terrain'
import { buildBusinessUnitScopeTree } from '@/features/auth/lib/business-unit-scope'
import { businessUnitTreeQueryKey, getBusinessUnitTree } from '@/features/auth/api'

import {
  buildClassificationLabelsFromTree,
} from '../lib/signal-feed-classification-selection'
import {
  EMPTY_SIGNAL_FEED_FILTERS,
  formatClassificationFilterSummary,
  formatStatusFilterSummary,
  normalizeSignalFeedFilters,
  type SignalFeedFilters,
} from '../lib/signal-feed-filters'
import { SignalFeedClassificationFilterSheet } from './signal-feed-classification-filter-sheet'
import { SignalFeedStatusFilterSheet } from './signal-feed-status-filter-sheet'

type SignalFeedFiltersBarProps = {
  establishmentId: string
  filters: SignalFeedFilters
  onFiltersChange: (filters: SignalFeedFilters) => void
}

export function SignalFeedFiltersBar({
  establishmentId,
  filters,
  onFiltersChange,
}: SignalFeedFiltersBarProps) {
  const [statusSheetOpen, setStatusSheetOpen] = useState(false)
  const [classificationSheetOpen, setClassificationSheetOpen] = useState(false)
  const normalizedFilters = normalizeSignalFeedFilters(filters)

  const treeQuery = useQuery({
    queryKey: businessUnitTreeQueryKey(establishmentId),
    queryFn: () => getBusinessUnitTree(establishmentId),
    enabled: Boolean(establishmentId),
  })

  const classificationLabels = useMemo(() => {
    if (!treeQuery.data) {
      return {
        labelByBusinessUnitKey: new Map<string, string>(),
        labelByActivitySubjectId: new Map<string, string>(),
      }
    }
    const businessUnits = buildBusinessUnitScopeTree(treeQuery.data).businessUnits
    return buildClassificationLabelsFromTree(businessUnits)
  }, [treeQuery.data])

  return (
    <>
      <div
        className="flex shrink-0 gap-2 border-t border-[#E8E6DF] bg-white px-3 py-2 pb-3"
        aria-label="Filtres des signaux"
      >
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
              classificationLabels.labelByBusinessUnitKey,
              classificationLabels.labelByActivitySubjectId,
            )}
            disabled={false}
            onClick={() => setClassificationSheetOpen(true)}
          />
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
          key={`classification-${normalizedFilters.businessUnitKeys.join(',')}-${normalizedFilters.activitySubjectIds.join(',')}`}
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
