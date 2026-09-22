import { useMemo, useState } from 'react'
import { LoaderCircle } from 'lucide-react'

import { useAuth } from '@/app/auth-provider'
import { TerrainHubSubheader } from '@/components/layout/terrain-hub-subheader'
import { TerrainHubTitleSlot } from '@/components/layout/terrain-hub-title-slot'
import {
  TerrainCollapsibleFeedSection,
  TerrainEmptyState,
  TerrainErrorState,
} from '@/components/ui/terrain'
import { useCollapsibleFeedSections } from '@/lib/use-collapsible-feed-sections'
import { resolveApiErrorMessage } from '@/lib/error-message'
import { SignalCard } from '../components/signal-card'
import { SignalFeedCardActionsSheet } from '../components/signal-feed-card-actions-sheet'
import {
  EMPTY_SIGNAL_FEED_FILTERS,
  SignalFeedFiltersBar,
} from '../components/signal-feed-filters-bar'
import { SignalFeedTabs } from '../components/signal-feed-tabs'
import { useLoadMoreSignalFeedSection, useSignalFeedQuery } from '../hooks'
import { useSignalFeedQuickActions } from '../hooks/use-signal-feed-quick-actions'
import { SignalsApiError } from '../api'
import { composeSignalFeedPresentation } from '../lib/signal-display'
import {
  hasActiveSignalFeedFilters,
  normalizeSignalFeedFilters,
  type SignalFeedFilters,
  type SignalFeedStatusFilter,
} from '../lib/signal-feed-filters'
import type { SignalFeedItem, SignalViewMode } from '../types'

const SIGNAL_FEED_DEFAULT_COLLAPSED_SECTIONS = ['interesting', 'resolved', 'canceled'] as const

type SignalFeedPageProps = {
  onOpenSignal: (signalId: string) => void
  establishmentId?: string | null
  source?: 'establishment' | 'cross'
}

export function SignalFeedPage({
  onOpenSignal,
  establishmentId: establishmentIdProp,
  source = 'establishment',
}: SignalFeedPageProps) {
  const auth = useAuth()
  const establishmentId =
    establishmentIdProp ?? auth.bootstrap?.active_membership?.establishment_id ?? null
  const membershipRole = auth.bootstrap?.active_membership?.role ?? null
  const isCross = source === 'cross'
  const [viewMode, setViewMode] = useState<SignalViewMode>('personal')
  const [filters, setFilters] = useState<SignalFeedFilters>(EMPTY_SIGNAL_FEED_FILTERS)

  const normalizedFilters = normalizeSignalFeedFilters(filters)
  const feedQuery = useSignalFeedQuery(establishmentId, viewMode, normalizedFilters, {
    source,
  })
  const loadMoreSection = useLoadMoreSignalFeedSection(
    establishmentId,
    viewMode,
    normalizedFilters,
    { source },
  )
  const filtersActive = hasActiveSignalFeedFilters(normalizedFilters)
  const quickActions = useSignalFeedQuickActions({
    establishmentId,
    viewMode,
    filters: normalizedFilters,
  })

  const presentation =
    (establishmentId || isCross) && feedQuery.isSuccess && feedQuery.data
      ? composeSignalFeedPresentation(feedQuery.data.sections)
      : null
  const pinnedItems = presentation?.pinnedItems ?? []
  const groups = presentation?.groups ?? null
  const unpinnedItems = presentation?.flatUnpinnedItems ?? []
  const sectionKeys = groups?.map((group) => group.status) ?? []
  const sectionExpansionResetToken = useMemo(
    () => `${viewMode}:${JSON.stringify(normalizedFilters)}`,
    [viewMode, normalizedFilters],
  )
  const { isExpanded, toggle } = useCollapsibleFeedSections(sectionKeys, {
    defaultCollapsedKeys: SIGNAL_FEED_DEFAULT_COLLAPSED_SECTIONS,
    resetToken: sectionExpansionResetToken,
  })

  if (!establishmentId && !isCross) {
    return (
      <p className="px-3 py-4 text-sm text-[#6b5f52]">Établissement non sélectionné.</p>
    )
  }

  const listClassName = 'flex flex-col gap-3 px-3'

  const renderItems = (items: SignalFeedItem[], variant: 'feed' | 'pinned' = 'feed') => (
    <div className={listClassName}>
      {items.map((item) => (
        <SignalCard
          key={item.id}
          item={item}
          variant={variant}
          onSelect={onOpenSignal}
          onOpenActions={isCross ? undefined : quickActions.openActions}
          showEstablishment={isCross}
        />
      ))}
    </div>
  )

  function handleClearFilters() {
    setFilters(EMPTY_SIGNAL_FEED_FILTERS)
  }

  function renderLoadMore(status: SignalFeedStatusFilter | null, hasMore: boolean) {
    if (!status || !hasMore) {
      return null
    }
    const isPending = loadMoreSection.isPending && loadMoreSection.variables === status
    return (
      <div className="flex justify-center py-4">
        <button
          type="button"
          className="text-xs font-semibold text-[#1B4FD8] disabled:opacity-60"
          onClick={() => loadMoreSection.mutate(status)}
          disabled={loadMoreSection.isPending}
        >
          {isPending ? 'Chargement…' : 'Charger plus'}
        </button>
      </div>
    )
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <TerrainHubTitleSlot enabled={!isCross}>
        <SignalFeedTabs viewMode={viewMode} onChange={setViewMode} />
      </TerrainHubTitleSlot>
      <TerrainHubSubheader>
        {isCross ? null : (
          <>
            <SignalFeedFiltersBar
              establishmentId={establishmentId}
              filters={filters}
              onFiltersChange={setFilters}
              membershipRole={membershipRole}
            />
            {filtersActive ? (
              <div className="border-t border-[#E8E6DF] px-3 pb-2 pt-0">
                <button
                  type="button"
                  onClick={handleClearFilters}
                  className="text-[11px] font-semibold text-[#1B4FD8]"
                >
                  Effacer les filtres
                </button>
              </div>
            ) : null}
          </>
        )}
      </TerrainHubSubheader>

      <div className="min-h-0 flex-1 overflow-y-auto overscroll-y-contain pb-3">
        {feedQuery.isLoading ? (
          <div className="flex items-center justify-center py-16 text-[#7D7B75]">
            <LoaderCircle className="h-6 w-6 animate-spin" />
          </div>
        ) : null}

        {feedQuery.isError ? (
          <TerrainErrorState
            className="mx-3 mt-3"
            message={resolveApiErrorMessage(feedQuery.error, SignalsApiError, 'Une erreur est survenue.')}
            onRetry={() => void feedQuery.refetch()}
          />
        ) : null}

        {feedQuery.isSuccess && presentation && !presentation.hasContent && filtersActive ? (
          <div className="mx-3 mt-3 space-y-2">
            <TerrainEmptyState
              title="Aucun résultat"
              description="Aucune observation ne correspond à ces filtres."
            />
            <button
              type="button"
              onClick={handleClearFilters}
              className="text-[11px] font-semibold text-[#1B4FD8]"
            >
              Effacer les filtres
            </button>
          </div>
        ) : null}

        {feedQuery.isSuccess && presentation && !presentation.hasContent && !filtersActive ? (
          <TerrainEmptyState
            className="mx-3 mt-3"
            title="Aucune observation active"
            description={
              viewMode === 'personal'
                ? 'Aucune observation ne correspond à votre zone pour le moment.'
                : 'Aucune observation active dans cet établissement.'
            }
          />
        ) : null}

        {feedQuery.isSuccess && presentation?.hasContent ? (
          <div className="flex flex-col gap-3 pt-5">
            {pinnedItems.length > 0 ? renderItems(pinnedItems, 'pinned') : null}

            {groups ? (
              <div className="flex flex-col gap-2">
                {groups.map((group) => (
                  <TerrainCollapsibleFeedSection
                    key={group.status}
                    label={group.label}
                    count={group.items.length}
                    dotVariant={group.dotVariant}
                    expanded={isExpanded(group.status)}
                    onToggle={() => toggle(group.status)}
                  >
                    {group.items.length > 0 ? renderItems(group.items) : null}
                    {renderLoadMore(group.status, group.hasMore)}
                  </TerrainCollapsibleFeedSection>
                ))}
              </div>
            ) : null}

            {!groups && unpinnedItems.length > 0 ? (
              <div>{renderItems(unpinnedItems)}</div>
            ) : null}

            {!groups
              ? renderLoadMore(presentation.flatStatus, presentation.flatHasMore)
              : null}
          </div>
        ) : null}
      </div>

      {quickActions.activeItem ? (
        <SignalFeedCardActionsSheet
          item={quickActions.activeItem}
          open={quickActions.actionsOpen}
          isPending={quickActions.isPending}
          errorMessage={quickActions.actionError}
          onClose={quickActions.closeActions}
          onSelectAction={quickActions.runAction}
        />
      ) : null}
    </div>
  )
}
