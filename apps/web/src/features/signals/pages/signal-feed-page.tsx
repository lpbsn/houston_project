import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { LoaderCircle } from 'lucide-react'

import { useAuth } from '@/app/auth-provider'
import { TerrainHubSubheader } from '@/components/layout/terrain-hub-subheader'
import { TerrainHubTitleSlot } from '@/components/layout/terrain-hub-title-slot'
import {
  FeedContinuationFooter,
  FeedPullIndicator,
  FeedRefreshButton,
  FeedUpdatesBanner,
  useFeedPullToRefresh,
} from '@/components/domain/feed-refresh-controls'
import {
  TerrainEmptyState,
  TerrainErrorState,
  TerrainSectionLabel,
} from '@/components/ui/terrain'
import { isDesktopWebLanding } from '@/features/auth/lib/authenticated-landing'
import { useLgViewport } from '@/lib/lg-viewport'
import { feedAuthorizationFingerprint } from '@/lib/feed-authorization'
import {
  focusContinuesPageOne,
  showRetainedPageOne,
  slotRequestCursorForItem,
} from '@/lib/feed-reading-window'
import { resolveApiErrorMessage } from '@/lib/error-message'
import { useFeedListSession } from '@/lib/use-feed-list-session'
import { cn } from '@/lib/utils'
import { SignalCard } from '../components/signal-card'
import { SignalFeedCardActionsSheet } from '../components/signal-feed-card-actions-sheet'
import { SignalFeedDesktopRow } from '../components/signal-feed-desktop-row'
import {
  EMPTY_SIGNAL_FEED_FILTERS,
  SignalFeedFiltersBar,
} from '../components/signal-feed-filters-bar'
import { SignalFeedPinnedCarousel } from '../components/signal-feed-pinned-carousel'
import { SignalFeedStatusChips } from '../components/signal-feed-status-chips'
import { SignalPinReplacementSheet } from '../components/signal-pin-replacement-sheet'
import { SignalFeedSkeletonList } from '../components/signal-feed-skeleton'
import { SignalFeedTabs } from '../components/signal-feed-tabs'
import { SignalQualifyRoutingSheet } from '../components/signal-qualify-routing-sheet'
import {
  useLoadMoreCrossSignalFeedPins,
  useLoadMoreSignalFeed,
  useRefreshSignalFeed,
  useResumeSignalFeed,
  useSignalFeedQuery,
} from '../hooks'
import {
  projectSignalFeedCache,
  removeSignalFromFeedCache,
  type SignalFeedCacheState,
} from '../lib/signal-feed-cache'
import { useSignalFeedQuickActions } from '../hooks/use-signal-feed-quick-actions'
import { useSignalQualifySheet } from '../hooks/use-signal-qualify-sheet'
import { SignalsApiError } from '../api'
import { groupLoadedSignalFeedItems } from '../lib/signal-display'
import {
  type SignalFeedCardActionId,
} from '../lib/signal-feed-card-actions'
import {
  hasActiveSignalFeedFilters,
  normalizeSignalFeedFilters,
  selectedSignalFeedStatus,
  type SignalFeedFilters,
} from '../lib/signal-feed-filters'
import {
  readSignalFeedReading,
  signalFeedReadingScopeKey,
  writeSignalFeedReading,
} from '../lib/signal-feed-reading-memory'
import type { SignalFeedItem, SignalViewMode } from '../types'

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
  const statusSelection = selectedSignalFeedStatus(normalizedFilters)
  const feedQuery = useSignalFeedQuery(establishmentId, viewMode, normalizedFilters, {
    source,
  })
  const loadMore = useLoadMoreSignalFeed(establishmentId, viewMode, normalizedFilters, {
    source,
  })
  const loadMorePins = useLoadMoreCrossSignalFeedPins(normalizedFilters)
  const refreshFeed = useRefreshSignalFeed(establishmentId, viewMode, normalizedFilters, {
    source,
  })
  const resumeFeed = useResumeSignalFeed(establishmentId, viewMode, normalizedFilters, {
    source,
  })
  const queryClient = useQueryClient()
  const feedQueryPrefix = useMemo(
    () =>
      isCross
        ? (['signals', 'cross-feed'] as const)
        : establishmentId
          ? (['signals', 'feed', establishmentId] as const)
          : null,
    [establishmentId, isCross],
  )
  const removeSignal = useCallback(
    (signalId: string) => {
      if (!feedQueryPrefix) {
        return
      }
      queryClient.setQueriesData<SignalFeedCacheState>({ queryKey: feedQueryPrefix }, (current) => {
        if (!current) {
          return current
        }
        return removeSignalFromFeedCache(current, signalId).feed
      })
    },
    [feedQueryPrefix, queryClient],
  )
  const feedSession = useFeedListSession({
    queryKeyPrefix: feedQueryPrefix,
    onRemove: removeSignal,
  })
  const authorizationFingerprint = feedAuthorizationFingerprint(
    auth.bootstrap?.memberships ?? auth.bootstrap?.active_membership,
  )
  const seenFingerprintRef = useRef(authorizationFingerprint)
  const approachArmedRef = useRef(true)
  const loadMoreRef = useRef<HTMLDivElement>(null)
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

  const feed = (establishmentId || isCross) && feedQuery.isSuccess ? feedQuery.data : null
  const pinnedItems =
    feed && statusSelection !== 'in_progress' ? (feed.pins ?? []) : []
  const listItems = feed?.items ?? []
  const groups = feed ? groupLoadedSignalFeedItems(listItems, statusSelection) : null
  const listHasMore = feed?.has_more === true
  const pinsHaveMore = isCross && feed?.pins_has_more === true
  const hasListContent = listItems.length > 0 || listHasMore
  const hasContent = pinnedItems.length > 0 || hasListContent
  const showsPageOne =
    !feed || !('readingWindow' in feed) || focusContinuesPageOne(feed.readingWindow)
  const preservedExpandedByKey = initialReading?.expandedByKey
  const canRememberReading = Boolean(establishmentId) || isCross

  const savedScrollTop = initialReading?.scrollTop ?? 0
  const feedHasContent = hasContent

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

  const setFeedReadingEdge = feedSession.setReadingEdge
  useEffect(() => {
    setFeedReadingEdge({
      atTop: (scrollRef.current?.scrollTop ?? 0) <= 0 && showsPageOne,
      interacting: loadMore.isPending || refreshFeed.isPending,
    })
  }, [
    feedHasContent,
    loadMore.isPending,
    refreshFeed.isPending,
    setFeedReadingEdge,
    showsPageOne,
  ])

  useEffect(() => {
    if (seenFingerprintRef.current === authorizationFingerprint) {
      return
    }
    seenFingerprintRef.current = authorizationFingerprint
    refreshFeed.mutate(undefined, {
      onSuccess: () => {
        feedSession.clearUpdates()
        if (scrollRef.current) {
          scrollRef.current.scrollTop = 0
        }
      },
    })
  }, [authorizationFingerprint, feedSession, refreshFeed])

  const anchorPhaseRef = useRef<'idle' | 'resuming' | 'seek' | 'done'>('idle')
  const [anchorTick, setAnchorTick] = useState(0)
  useEffect(() => {
    if (anchorPhaseRef.current === 'done' || anchorPhaseRef.current === 'resuming') {
      return
    }
    const anchorId = initialReading?.anchorId
    if (!anchorId || !feed) {
      return
    }
    const scrollTo = (id: string) => {
      scrollRef.current
        ?.querySelector(`[data-feed-item="${id}"]`)
        ?.scrollIntoView({ block: 'center' })
    }
    if (
      feed.items.some((item) => item.id === anchorId) ||
      feed.pins?.some((item) => item.id === anchorId)
    ) {
      anchorPhaseRef.current = 'done'
      scrollTo(anchorId)
      return
    }
    const resumeCursor = initialReading?.resumeCursor
    if (resumeCursor && anchorPhaseRef.current === 'idle') {
      anchorPhaseRef.current = 'resuming'
      resumeFeed.mutate(resumeCursor, {
        onSettled: () => {
          anchorPhaseRef.current = 'seek'
          setAnchorTick((tick) => tick + 1)
        },
      })
      return
    }
    const neighborId = initialReading?.neighborId
    if (neighborId && feed.items.some((item) => item.id === neighborId)) {
      scrollTo(neighborId)
    }
    anchorPhaseRef.current = 'done'
  }, [anchorTick, feed, initialReading, resumeFeed])

  useEffect(() => {
    const target = loadMoreRef.current
    const root = scrollRef.current
    if (!target || !root || !listHasMore || loadMore.isPending || loadMore.isError) {
      return
    }
    if (typeof IntersectionObserver === 'undefined') {
      return
    }
    const observer = new IntersectionObserver(
      (entries) => {
        if (!entries.some((entry) => entry.isIntersecting) || !approachArmedRef.current) {
          return
        }
        approachArmedRef.current = false
        loadMore.mutate()
      },
      { root, rootMargin: '400px 0px' },
    )
    observer.observe(target)
    return () => observer.disconnect()
  }, [listHasMore, loadMore])

  const pullToRefresh = useFeedPullToRefresh({
    enabled: !isDesktopWeb,
    scrollerRef: scrollRef,
    onRefresh: () => {
      refreshFeed.mutate(undefined, {
        onSuccess: () => {
          feedSession.clearUpdates()
          if (scrollRef.current) {
            scrollRef.current.scrollTop = 0
          }
        },
      })
    },
  })

  useEffect(() => {
    if (!canRememberReading) {
      return
    }
    writeSignalFeedReading(readingScopeKey, {
      viewMode,
      filters: normalizedFilters,
      ...(preservedExpandedByKey ? { expandedByKey: preservedExpandedByKey } : {}),
      scrollTop: restoredScrollRef.current
        ? (scrollRef.current?.scrollTop ?? 0)
        : savedScrollTop,
    })
  }, [
    canRememberReading,
    normalizedFilters,
    preservedExpandedByKey,
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

  function openSignal(signalId: string) {
    const listIndex = listItems.findIndex((item) => item.id === signalId)
    const sourceItems = listIndex >= 0 ? listItems : pinnedItems
    const index = sourceItems.findIndex((item) => item.id === signalId)
    const neighbor = sourceItems[index + 1] ?? sourceItems[index - 1]
    const resumeCursor =
      listIndex >= 0 && feed && 'readingWindow' in feed
        ? slotRequestCursorForItem(feed.readingWindow, signalId, (item) => item.id)
        : undefined
    if (canRememberReading) {
      writeSignalFeedReading(readingScopeKey, {
        anchorId: signalId,
        neighborId: neighbor?.id ?? null,
        resumeCursor: typeof resumeCursor === 'string' ? resumeCursor : null,
        authorizationFingerprint,
      })
    }
    onOpenSignal(signalId)
  }

  const renderItems = (items: SignalFeedItem[], variant: 'feed' | 'pinned' = 'feed') => (
    <div className={listClassName}>
      {items.map((item) => (
        <div key={item.id} data-feed-item={item.id}>
        {isDesktopWeb ? (
          <SignalFeedDesktopRow
            key={item.id}
            item={item}
            pinned={variant === 'pinned'}
            onSelect={openSignal}
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
            onSelect={openSignal}
            onOpenActions={isCross ? undefined : quickActions.openActions}
            showEstablishment={isCross}
            viewMode={viewMode}
          />
        )}
        </div>
      ))}
    </div>
  )

  function handleClearFilters() {
    setFilters(EMPTY_SIGNAL_FEED_FILTERS)
  }

  function requestNextPage() {
    approachArmedRef.current = false
    loadMore.mutate()
  }

  function renderListContinuation() {
    const mismatch =
      loadMore.isError &&
      loadMore.error instanceof SignalsApiError &&
      loadMore.error.code === 'cursor_context_mismatch'
    return (
      <div ref={loadMoreRef}>
        <FeedContinuationFooter
          hasMore={listHasMore && !loadMore.isError}
          isLoadingMore={loadMore.isPending}
          hasItems={listItems.length > 0}
          errorMessage={loadMore.isError ? 'La suite n’a pas pu être chargée.' : null}
          onLoadMore={requestNextPage}
          onRetry={() => {
            if (mismatch) {
              void feedQuery.refetch().finally(() => loadMore.reset())
              return
            }
            loadMore.mutate()
          }}
        />
      </div>
    )
  }

  const mobileSafePad = !isDesktopWeb

  return (
    <div className="flex h-full min-h-0 flex-col">
      <TerrainHubTitleSlot enabled={!isCross}>
        <SignalFeedTabs
          viewMode={viewMode}
          onChange={setViewMode}
          size={isDesktopWeb ? 'default' : 'compact'}
        />
      </TerrainHubTitleSlot>
      {!isCross && quickActions.pinReplacement ? (
        <SignalPinReplacementSheet
          open
          presentation={isDesktopWeb ? 'dialog' : 'sheet'}
          candidates={quickActions.pinReplacement.candidates}
          isPending={quickActions.isPending}
          onClose={quickActions.closePinReplacement}
          onReplace={quickActions.replacePin}
        />
      ) : null}
      <TerrainHubSubheader>
        <SignalFeedStatusChips
          filters={filters}
          counts={feed?.counts}
          layout={isDesktopWeb ? 'wrap' : 'scroll'}
          className={isDesktopWeb ? 'bg-white px-4 py-2' : cn('bg-white py-2', MOBILE_FEED_INSET_X)}
          onChange={setFilters}
        />
        {!isCross && establishmentId ? (
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
            {isDesktopWeb ? (
              <div className="px-4 pb-2">
                <FeedRefreshButton
                  onRefresh={() => {
                    refreshFeed.mutate(undefined, {
                      onSuccess: () => {
                        feedSession.clearUpdates()
                        if (scrollRef.current) {
                          scrollRef.current.scrollTop = 0
                        }
                      },
                    })
                  }}
                  pending={refreshFeed.isPending}
                />
              </div>
            ) : null}
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
        ) : null}
      </TerrainHubSubheader>

      <div
        ref={scrollRef}
        data-testid="signal-feed-scroll"
        className="min-h-0 flex-1 overflow-y-auto overscroll-y-contain pb-3"
        onScroll={(event) => {
          approachArmedRef.current = true
          feedSession.setReadingEdge({
            atTop: event.currentTarget.scrollTop <= 0 && showsPageOne,
            interacting: loadMore.isPending || refreshFeed.isPending,
          })
          if (!canRememberReading || !restoredScrollRef.current) {
            return
          }
          writeSignalFeedReading(readingScopeKey, {
            scrollTop: event.currentTarget.scrollTop,
            authorizationFingerprint,
          })
        }}
        {...pullToRefresh.pointerProps}
      >
        <FeedPullIndicator distance={pullToRefresh.pullDistance} refreshing={refreshFeed.isPending} />
        {feedSession.updatesAvailable ? (
          <FeedUpdatesBanner
            onRefresh={() => {
              refreshFeed.mutate(undefined, {
                onSuccess: () => {
                  feedSession.clearUpdates()
                  if (scrollRef.current) {
                    scrollRef.current.scrollTop = 0
                  }
                },
              })
            }}
          />
        ) : null}
        {refreshFeed.isError ? (
          <TerrainErrorState
            className="mx-3 mt-3"
            message="L’actualisation n’a pas abouti. Les données affichées sont inchangées."
            onRetry={() => refreshFeed.mutate()}
          />
        ) : null}
        {feed && 'readingWindow' in feed && !focusContinuesPageOne(feed.readingWindow) ? (
          <div className="flex justify-center px-3 pt-3">
            <button
              type="button"
              className="min-h-11 text-sm font-semibold text-[#1B4FD8]"
              onClick={() => {
                if (!feedQueryPrefix) {
                  return
                }
                queryClient.setQueriesData<SignalFeedCacheState>(
                  { queryKey: feedQueryPrefix },
                  (current) =>
                    current
                      ? projectSignalFeedCache({
                          ...current,
                          readingWindow: showRetainedPageOne(current.readingWindow),
                        })
                      : current,
                )
                if (scrollRef.current) {
                  scrollRef.current.scrollTop = 0
                }
              }}
            >
              Haut du feed
            </button>
          </div>
        ) : null}
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

        {feedQuery.isSuccess && !hasContent && filtersActive ? (
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

        {feedQuery.isSuccess && !hasContent && !filtersActive ? (
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

        {feedQuery.isSuccess && hasContent ? (
          <div className="flex flex-col gap-3 pt-5">
            {pinnedItems.length > 0 ? (
              <div className="flex flex-col gap-2">
                <TerrainSectionLabel
                  className={isDesktopWeb ? 'px-4' : MOBILE_FEED_INSET_X}
                  dotVariant="warning"
                >
                  {feed?.counts
                    ? `Épinglées · ${feed.counts.pinned}`
                    : `Épinglées · ${pinnedItems.length}`}
                </TerrainSectionLabel>
                <SignalFeedPinnedCarousel
                  items={pinnedItems}
                  onSelect={openSignal}
                  onOpenActions={isCross ? undefined : quickActions.openActions}
                  showEstablishment={isCross}
                  viewMode={viewMode}
                  className={isDesktopWeb ? 'px-4' : MOBILE_FEED_INSET_X}
                />
                {pinsHaveMore ? (
                  <div className="flex justify-center px-3 py-1">
                    <button
                      type="button"
                      className="min-h-11 text-sm font-semibold text-[#1B4FD8] disabled:opacity-60"
                      onClick={() => loadMorePins.mutate()}
                      disabled={loadMorePins.isPending}
                    >
                      {loadMorePins.isPending ? 'Chargement…' : 'Afficher d’autres épingles'}
                    </button>
                  </div>
                ) : null}
                {loadMorePins.isError ? (
                  <TerrainErrorState
                    className="mx-3"
                    message="La suite des épingles n’a pas pu être chargée."
                    onRetry={() => {
                      if (
                        loadMorePins.error instanceof SignalsApiError &&
                        loadMorePins.error.code === 'cursor_context_mismatch'
                      ) {
                        void feedQuery.refetch().finally(() => loadMorePins.reset())
                        return
                      }
                      loadMorePins.mutate()
                    }}
                  />
                ) : null}
              </div>
            ) : null}

            {listItems.length === 0 && !listHasMore && pinnedItems.length > 0 ? (
              <TerrainEmptyState
                className="mx-3"
                title="Aucune autre observation"
                description="Les observations épinglées sont affichées au-dessus."
              />
            ) : null}

            {groups ? (
              <div className="flex flex-col gap-2">
                {groups.map((group) => (
                  <div key={group.status} className="flex flex-col gap-2">
                    <TerrainSectionLabel
                      className={isDesktopWeb ? 'px-4' : MOBILE_FEED_INSET_X}
                      dotVariant={group.dotVariant}
                    >
                      {group.label}
                    </TerrainSectionLabel>
                    {renderItems(group.items)}
                  </div>
                ))}
              </div>
            ) : listItems.length > 0 ? (
              <div>{renderItems(listItems)}</div>
            ) : null}

            {renderListContinuation()}
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
