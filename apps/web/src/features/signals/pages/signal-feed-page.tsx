import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { LoaderCircle } from 'lucide-react'

import { useAuth } from '@/app/auth-provider'
import { TerrainHubSubheader } from '@/components/layout/terrain-hub-subheader'
import { TerrainHubTitleSlot } from '@/components/layout/terrain-hub-title-slot'
import {
  TerrainCollapsibleFeedSection,
  TerrainEmptyState,
  TerrainErrorState,
} from '@/components/ui/terrain'
import { isDesktopWebLanding } from '@/features/auth/lib/authenticated-landing'
import { useCollapsibleFeedSections } from '@/lib/use-collapsible-feed-sections'
import { useLgViewport } from '@/lib/lg-viewport'
import { resolveApiErrorMessage } from '@/lib/error-message'
import { cn } from '@/lib/utils'
import { SignalCard } from '../components/signal-card'
import { SignalFeedCardActionsSheet } from '../components/signal-feed-card-actions-sheet'
import { SignalFeedDesktopRow } from '../components/signal-feed-desktop-row'
import {
  EMPTY_SIGNAL_FEED_FILTERS,
  SignalFeedFiltersBar,
} from '../components/signal-feed-filters-bar'
import { SignalFeedPinnedCarousel } from '../components/signal-feed-pinned-carousel'
import { SignalFeedSkeletonList } from '../components/signal-feed-skeleton'
import { SignalFeedTabs } from '../components/signal-feed-tabs'
import { SignalQualifyRoutingSheet } from '../components/signal-qualify-routing-sheet'
import { useLoadMoreSignalFeedSection, useSignalFeedQuery } from '../hooks'
import { useSignalFeedQuickActions } from '../hooks/use-signal-feed-quick-actions'
import { useSignalQualifySheet } from '../hooks/use-signal-qualify-sheet'
import { SignalsApiError } from '../api'
import { composeSignalFeedPresentation } from '../lib/signal-display'
import {
  type SignalFeedCardActionId,
} from '../lib/signal-feed-card-actions'
import {
  hasActiveSignalFeedFilters,
  normalizeSignalFeedFilters,
  type SignalFeedFilters,
  type SignalFeedStatusFilter,
} from '../lib/signal-feed-filters'
import {
  readSignalFeedReading,
  signalFeedReadingScopeKey,
  writeSignalFeedReading,
} from '../lib/signal-feed-reading-memory'
import type { SignalFeedItem, SignalViewMode } from '../types'

const SIGNAL_FEED_DEFAULT_COLLAPSED_SECTIONS = ['interesting', 'resolved', 'canceled'] as const

/** Horizontal inset for mobile feed content — replaces fixed px-3; one pad, no stacking. */
const MOBILE_FEED_INSET_X =
  'pl-[max(0.75rem,var(--app-safe-left))] pr-[max(0.75rem,var(--app-safe-right))]'

type SignalFeedPageProps = {
  onOpenSignal: (signalId: string) => void
  onNavigate: (pathname: string, options?: { replace?: boolean }) => void
  establishmentId?: string | null
  source?: 'establishment' | 'cross'
}

/**
 * Remount when the reading scope changes so filters/scroll of establishment A
 * cannot leak into B (or Cross) when `/signals` stays mounted across a switch.
 */
export function SignalFeedPage({
  onOpenSignal,
  onNavigate,
  establishmentId: establishmentIdProp,
  source = 'establishment',
}: SignalFeedPageProps) {
  const auth = useAuth()
  const establishmentId =
    establishmentIdProp ?? auth.bootstrap?.active_membership?.establishment_id ?? null
  const readingScopeKey = signalFeedReadingScopeKey(source, establishmentId)
  return (
    <SignalFeedPageContent
      key={readingScopeKey}
      onOpenSignal={onOpenSignal}
      onNavigate={onNavigate}
      establishmentId={establishmentId}
      source={source}
    />
  )
}

function SignalFeedPageContent({
  onOpenSignal,
  onNavigate,
  establishmentId,
  source,
}: {
  onOpenSignal: (signalId: string) => void
  onNavigate: (pathname: string, options?: { replace?: boolean }) => void
  establishmentId: string | null
  source: 'establishment' | 'cross'
}) {
  const auth = useAuth()
  const membershipRole = auth.bootstrap?.active_membership?.role ?? null
  const isCross = source === 'cross'
  const isDesktopWeb = isDesktopWebLanding(useLgViewport())
  const readingScopeKey = signalFeedReadingScopeKey(source, establishmentId)
  const [initialReading] = useState(() => readSignalFeedReading(readingScopeKey))
  const scrollRef = useRef<HTMLDivElement>(null)
  const restoredScrollRef = useRef(false)
  const [viewMode, setViewMode] = useState<SignalViewMode>(
    initialReading?.viewMode ?? 'personal',
  )
  const [filters, setFilters] = useState<SignalFeedFilters>(
    initialReading?.filters ?? EMPTY_SIGNAL_FEED_FILTERS,
  )

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
  const qualifySheet = useSignalQualifySheet({
    establishmentId,
    onNavigate,
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
  const { isExpanded, toggle, expandedByKey } = useCollapsibleFeedSections(sectionKeys, {
    defaultCollapsedKeys: SIGNAL_FEED_DEFAULT_COLLAPSED_SECTIONS,
    resetToken: sectionExpansionResetToken,
    initialExpandedByKey: initialReading?.expandedByKey,
  })
  const canRememberReading = Boolean(establishmentId) || isCross

  const savedScrollTop = initialReading?.scrollTop ?? 0
  const feedHasContent = presentation?.hasContent === true

  useLayoutEffect(() => {
    if (restoredScrollRef.current) {
      return
    }
    const scroller = scrollRef.current
    if (!scroller) {
      return
    }
    if (savedScrollTop > 0 && !feedHasContent) {
      return
    }
    scroller.scrollTop = savedScrollTop
    restoredScrollRef.current = true
  }, [feedHasContent, savedScrollTop])

  useEffect(() => {
    if (!canRememberReading) {
      return
    }
    writeSignalFeedReading(readingScopeKey, {
      viewMode,
      filters: normalizedFilters,
      expandedByKey,
      scrollTop: restoredScrollRef.current
        ? (scrollRef.current?.scrollTop ?? 0)
        : savedScrollTop,
    })
  }, [
    canRememberReading,
    expandedByKey,
    normalizedFilters,
    readingScopeKey,
    savedScrollTop,
    viewMode,
    feedHasContent,
  ])

  if (!establishmentId && !isCross) {
    return (
      <p className="px-3 py-4 text-sm text-[#6b5f52]">Établissement non sélectionné.</p>
    )
  }

  const listClassName = isDesktopWeb
    ? 'flex flex-col gap-1 px-4'
    : cn('flex flex-col gap-3', MOBILE_FEED_INSET_X)

  function handleFeedAction(
    item: SignalFeedItem,
    actionId: SignalFeedCardActionId,
  ) {
    if (actionId === 'qualify') {
      quickActions.closeActions()
      void qualifySheet.openForSignal(item.id)
      return 'close' as const
    }
    return quickActions.runAction(actionId, item)
  }

  const renderItems = (items: SignalFeedItem[], variant: 'feed' | 'pinned' = 'feed') => (
    <div className={listClassName}>
      {items.map((item) =>
        isDesktopWeb ? (
          <SignalFeedDesktopRow
            key={item.id}
            item={item}
            pinned={variant === 'pinned'}
            onSelect={onOpenSignal}
            showEstablishment={isCross}
            actionsPending={quickActions.isPending || qualifySheet.opening}
            actionsOpen={
              !isCross &&
              quickActions.actionsOpen &&
              quickActions.activeItem?.id === item.id
            }
            actionError={
              !isCross && quickActions.activeItem?.id === item.id
                ? quickActions.actionError ??
                  (qualifySheet.signalId === item.id ? qualifySheet.errorMessage : null)
                : null
            }
            onActionsOpenChange={
              isCross
                ? undefined
                : (open) => {
                    if (open) {
                      quickActions.openActions(item)
                      return
                    }
                    quickActions.closeActions()
                  }
            }
            onRunAction={
              isCross
                ? undefined
                : (feedItem, actionId) => handleFeedAction(feedItem, actionId)
            }
          />
        ) : (
          <SignalCard
            key={item.id}
            item={item}
            variant={variant}
            onSelect={onOpenSignal}
            onOpenActions={isCross ? undefined : quickActions.openActions}
            showEstablishment={isCross}
            viewMode={viewMode}
          />
        ),
      )}
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
      <div className="flex justify-center px-3 py-3">
        <button
          type="button"
          className="min-h-11 rounded-full border border-[#1B4FD8]/25 bg-[#EEF4FF] px-5 text-sm font-semibold text-[#1B4FD8] disabled:opacity-60"
          onClick={() => loadMoreSection.mutate(status)}
          disabled={loadMoreSection.isPending}
        >
          {isPending ? 'Chargement…' : 'Afficher plus'}
        </button>
      </div>
    )
  }

  const mobileSafePad = !isDesktopWeb

  return (
    <div className="flex h-full min-h-0 flex-col">
      <TerrainHubTitleSlot enabled={!isCross}>
        <SignalFeedTabs viewMode={viewMode} onChange={setViewMode} />
      </TerrainHubTitleSlot>
      <TerrainHubSubheader>
        {isCross || !establishmentId ? null : (
          <>
            <SignalFeedFiltersBar
              establishmentId={establishmentId}
              filters={filters}
              onFiltersChange={setFilters}
              membershipRole={membershipRole}
              showReset={!isDesktopWeb}
              onReset={handleClearFilters}
              contentClassName={mobileSafePad ? MOBILE_FEED_INSET_X : undefined}
            />
            {isDesktopWeb && filtersActive ? (
              <div className="border-t border-[#E8E6DF] px-4 pb-2 pt-0">
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

      <div
        ref={scrollRef}
        data-testid="signal-feed-scroll"
        className="min-h-0 flex-1 overflow-y-auto overscroll-y-contain pb-3"
        onScroll={(event) => {
          if (!canRememberReading || !restoredScrollRef.current) {
            return
          }
          writeSignalFeedReading(readingScopeKey, { scrollTop: event.currentTarget.scrollTop })
        }}
      >
        {feedQuery.isLoading ? (
          isDesktopWeb ? (
            <div className="flex items-center justify-center py-16 text-[#7D7B75]">
              <LoaderCircle className="h-6 w-6 animate-spin" />
            </div>
          ) : (
            <SignalFeedSkeletonList className={MOBILE_FEED_INSET_X} />
          )
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
              {isDesktopWeb ? 'Effacer les filtres' : 'Réinitialiser'}
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
            {pinnedItems.length > 0 ? (
              isDesktopWeb ? (
                renderItems(pinnedItems, 'pinned')
              ) : (
                <SignalFeedPinnedCarousel
                  items={pinnedItems}
                  onSelect={onOpenSignal}
                  onOpenActions={isCross ? undefined : quickActions.openActions}
                  showEstablishment={isCross}
                  viewMode={viewMode}
                  className={MOBILE_FEED_INSET_X}
                />
              )
            ) : null}

            {groups ? (
              <div className="flex flex-col gap-2">
                {groups.map((group) => (
                  <TerrainCollapsibleFeedSection
                    key={group.status}
                    label={group.label}
                    count={group.hasMore ? undefined : group.items.length}
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

      {!isDesktopWeb && quickActions.activeItem ? (
        <SignalFeedCardActionsSheet
          item={quickActions.activeItem}
          open={quickActions.actionsOpen}
          isPending={quickActions.isPending || qualifySheet.opening}
          errorMessage={
            quickActions.actionError ??
            (qualifySheet.signalId === quickActions.activeItem.id
              ? qualifySheet.errorMessage
              : null)
          }
          onClose={quickActions.closeActions}
          onSelectAction={(actionId) =>
            handleFeedAction(quickActions.activeItem!, actionId)
          }
        />
      ) : null}

      {establishmentId && qualifySheet.open && qualifySheet.signal ? (
        <SignalQualifyRoutingSheet
          key={qualifySheet.signal.id}
          open={qualifySheet.open}
          establishmentId={establishmentId}
          signal={qualifySheet.signal}
          isPending={qualifySheet.isPending}
          errorMessage={qualifySheet.errorMessage}
          onClose={qualifySheet.close}
          onSubmit={(patch) => void qualifySheet.submit(patch)}
        />
      ) : null}
    </div>
  )
}
