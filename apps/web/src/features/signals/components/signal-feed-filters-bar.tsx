import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'

import { TerrainFilterSlot } from '@/components/ui/terrain'
import { buildOperationalScopeTree } from '@/features/auth/lib/membership-scope'
import { getOperationalTaxonomy, operationalTaxonomyQueryKey } from '@/features/auth/api'

import { buildLabelByKeyFromTree } from '../lib/signal-feed-category-selection'

import {
  EMPTY_SIGNAL_FEED_FILTERS,
  formatCategoryFilterSummary,
  formatStatusFilterSummary,
  normalizeSignalFeedFilters,
  type SignalFeedFilters,
} from '../lib/signal-feed-filters'
import { SignalFeedCategoryFilterSheet } from './signal-feed-category-filter-sheet'
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
  const [categorySheetOpen, setCategorySheetOpen] = useState(false)

  const taxonomyQuery = useQuery({
    queryKey: operationalTaxonomyQueryKey(establishmentId),
    queryFn: () => getOperationalTaxonomy(establishmentId),
    staleTime: 60_000,
  })

  const labelByKey = useMemo(() => {
    if (!taxonomyQuery.data) {
      return new Map<string, string>()
    }
    return buildLabelByKeyFromTree(buildOperationalScopeTree(taxonomyQuery.data))
  }, [taxonomyQuery.data])

  const normalizedFilters = normalizeSignalFeedFilters(filters)

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
            onClick={() => {
              setCategorySheetOpen(false)
              setStatusSheetOpen(true)
            }}
          />
        </div>
        <div className="flex flex-1" data-filter-kind="category">
          <TerrainFilterSlot
            label="Catégorie"
            value={formatCategoryFilterSummary(normalizedFilters, labelByKey)}
            disabled={false}
            onClick={() => {
              setStatusSheetOpen(false)
              setCategorySheetOpen(true)
            }}
          />
        </div>
      </div>

      {statusSheetOpen ? (
        <SignalFeedStatusFilterSheet
          key={`status-${normalizedFilters.statuses.join(',')}`}
          appliedFilters={normalizedFilters}
          onClose={() => setStatusSheetOpen(false)}
          onApply={(next) => onFiltersChange(normalizeSignalFeedFilters(next))}
        />
      ) : null}

      {categorySheetOpen ? (
        <SignalFeedCategoryFilterSheet
          key={[
            normalizedFilters.moduleKeys.join(','),
            normalizedFilters.domainKeys.join(','),
            normalizedFilters.subjectKeys.join(','),
          ].join('|')}
          establishmentId={establishmentId}
          appliedFilters={normalizedFilters}
          onClose={() => setCategorySheetOpen(false)}
          onApply={(next) => onFiltersChange(normalizeSignalFeedFilters(next))}
        />
      ) : null}
    </>
  )
}

export { EMPTY_SIGNAL_FEED_FILTERS }
