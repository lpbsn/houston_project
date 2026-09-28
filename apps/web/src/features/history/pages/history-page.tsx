import { useEffect, useRef } from 'react'
import { LoaderCircle } from 'lucide-react'

import { serializeAppRoute, useAppRoute } from '@/app/app-routes'
import { useAuth } from '@/app/auth-provider'
import type { TerrainScope } from '@/app/scoped-terrain'
import {
  FeedPullIndicator,
  useFeedPullToRefresh,
} from '@/components/domain/feed-refresh-controls'
import {
  TerrainEmptyState,
  TerrainErrorState,
  TerrainSegmentedControl,
} from '@/components/ui/terrain'
import { isDesktopWebLanding } from '@/features/auth/lib/authenticated-landing'
import { HistoryApiError } from '@/features/history/api'
import { useHistoryList } from '@/features/history/hooks'
import {
  groupHistoryItems,
  reconcileHistoryItems,
} from '@/features/history/lib/history-groups'
import {
  historyReturnSearch,
  parseHistorySearch,
  serializeHistorySearch,
  type HistoryKind,
  type HistoryPeriod,
  type HistoryUrlState,
  type HistoryViewMode,
} from '@/features/history/lib/history-url-state'
import { resolveApiErrorMessage } from '@/lib/error-message'
import { useLgViewport } from '@/lib/lg-viewport'
import { cn } from '@/lib/utils'

type HistoryPageProps = {
  scope: TerrainScope | null
}

type HistoryRow = {
  id: string
  title: string
  terminal_at: string | null
  establishment_name: string
  termination_origin: string
  termination_actor_display_name: string | null
}

function historyRows(
  pages: { items: HistoryRow[] }[] | undefined,
): HistoryRow[] {
  return reconcileHistoryItems(pages?.flatMap((page) => page.items) ?? [])
}

const PERIODS: { value: HistoryPeriod; label: string }[] = [
  { value: '7', label: '7 j' },
  { value: '30', label: '30 j' },
  { value: '90', label: '90 j' },
  { value: 'custom', label: 'Dates' },
  { value: 'all', label: 'Toutes' },
]

function originLabel(origin: string, actor: string | null): string {
  const path =
    origin === 'manual'
      ? 'Manuelle'
      : origin === 'resolution_request'
        ? 'Demande de résolution'
        : origin === 'action_plan'
          ? 'Plan d’action'
          : origin === 'schedule_sync'
            ? 'Synchronisation de planning'
            : 'Origine inconnue'
  if (origin === 'unknown' || !actor) {
    return path
  }
  return `${path} · ${actor}`
}

function statusOptions(kind: HistoryKind): { value: string; label: string }[] {
  if (kind === 'signals') {
    return [
      { value: 'all', label: 'Tous' },
      { value: 'resolved', label: 'Résolues' },
      { value: 'canceled', label: 'Annulées' },
    ]
  }
  return [
    { value: 'all', label: 'Tous' },
    { value: 'done', label: 'Terminées' },
    { value: 'canceled', label: 'Annulées' },
  ]
}

export function HistoryPage({ scope }: HistoryPageProps) {
  const auth = useAuth()
  const { route, search, navigate } = useAppRoute()
  const isDesktopWeb = isDesktopWebLanding(useLgViewport())
  const inheritedEstablishmentId = auth.bootstrap?.active_membership?.establishment_id ?? null
  const source = scope?.type === 'cross' ? 'cross' : 'establishment'
  const establishmentId =
    scope?.type === 'establishment'
      ? scope.establishmentId
      : scope?.type === 'cross'
        ? null
        : inheritedEstablishmentId
  const needsSelection = source === 'establishment' && !establishmentId
  const url = parseHistorySearch(search, source)
  const list = useHistoryList({
    source,
    establishmentId,
    kind: url.kind,
    viewMode: url.viewMode,
    period: url.period,
    status: url.status,
    from: url.from || undefined,
    to: url.to || undefined,
    enabled: !needsSelection,
  })

  const items = historyRows(list.data?.pages)
  const groups = groupHistoryItems(items)
  const undatedCount = list.data?.pages[0]?.undated_count ?? 0
  const customIncomplete = url.period === 'custom' && (!url.from || !url.to)
  const stalled =
    list.data?.pages.at(-1)?.has_more === true && list.hasNextPage === false && !list.isFetching
  const scopeLabel =
    source === 'cross'
      ? 'Cross-établissement'
      : (auth.memberships.find((membership) => membership.establishment_id === establishmentId)
          ?.establishment_name ?? 'Établissement')

  const scrollRef = useRef<HTMLDivElement>(null)
  const loadMoreRef = useRef<HTMLDivElement>(null)

  async function refreshHistory() {
    try {
      await list.refresh()
      scrollRef.current?.scrollTo({ top: 0 })
    } catch {
      // The mutation exposes its error while preserving the currently displayed pages.
    }
  }

  function replaceState(next: HistoryUrlState) {
    const pathname = serializeAppRoute(route).split('?')[0] ?? '/general/history'
    navigate(`${pathname}${serializeHistorySearch(next, source)}`, { replace: true })
  }

  function openItem(id: string) {
    const nextSearch = historyReturnSearch({ ...url, anchorId: id }, source)
    if (url.kind === 'signals') {
      const path =
        source === 'cross'
          ? `/cross/signals/${id}`
          : establishmentId
            ? `/e/${establishmentId}/signals/${id}`
            : `/signals/${id}`
      navigate(`${path}${nextSearch}`)
      return
    }
    const path =
      source === 'cross'
        ? `/cross/execution/${id}`
        : establishmentId
          ? `/e/${establishmentId}/execution/${id}`
          : `/action-plans/executions/${id}`
    navigate(`${path}${nextSearch}`)
  }

  useEffect(() => {
    const anchorId = url.anchorId
    if (!anchorId || items.length === 0) {
      return
    }
    const node = scrollRef.current?.querySelector(`[data-history-id="${anchorId}"]`)
    if (node instanceof HTMLElement) {
      node.scrollIntoView({ block: 'center' })
    }
  }, [url.anchorId, items.length])

  const { fetchNextPage, hasNextPage, isFetchingNextPage, isError } = list
  useEffect(() => {
    const target = loadMoreRef.current
    const root = scrollRef.current
    if (!target || !root || !hasNextPage || isFetchingNextPage || isError) {
      return
    }
    if (typeof IntersectionObserver === 'undefined') {
      return
    }
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          void fetchNextPage()
        }
      },
      { root, rootMargin: '400px 0px' },
    )
    observer.observe(target)
    return () => observer.disconnect()
  }, [fetchNextPage, hasNextPage, isFetchingNextPage, isError])

  const pullToRefresh = useFeedPullToRefresh({
    enabled: !isDesktopWeb && !needsSelection && !customIncomplete,
    scrollerRef: scrollRef,
    onRefresh: () => {
      void refreshHistory()
    },
  })

  if (needsSelection) {
    const choices = auth.memberships.filter((membership) => membership.status === 'active')
    return (
      <div className="flex flex-col gap-3 px-3 py-4">
        <p className="text-sm text-[#6b5f52]">
          Choisissez l’établissement à consulter. L’historique Cross n’est pas ouvert depuis cet écran.
        </p>
        {choices.length === 0 ? (
          <TerrainEmptyState title="Aucun établissement" description="Aucun établissement actif n’est disponible." />
        ) : (
          <div className="flex flex-col gap-2">
            {choices.map((membership) => (
              <button
                key={membership.establishment_id}
                type="button"
                className="min-h-11 rounded-xl border border-[#E8E6DF] bg-white px-4 text-left text-sm font-semibold"
                onClick={() => navigate(`/e/${membership.establishment_id}/general/history`)}
              >
                {membership.establishment_name}
              </button>
            ))}
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex flex-col gap-3 border-b border-[#E8E6DF] px-3 py-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-[#7D7B75]">{scopeLabel}</p>
        <TerrainSegmentedControl
          ariaLabel="Type d’historique"
          value={url.kind}
          onChange={(kind) =>
            replaceState({
              ...url,
              kind: kind as HistoryKind,
              status: 'all',
              anchorId: null,
            })
          }
          options={[
            { value: 'signals', label: 'Observations' },
            { value: 'executions', label: 'Exécutions' },
          ]}
        />
        <TerrainSegmentedControl
          ariaLabel="Mode de vue"
          size="compact"
          value={url.viewMode}
          onChange={(viewMode) =>
            replaceState({ ...url, viewMode: viewMode as HistoryViewMode, anchorId: null })
          }
          options={[
            { value: 'personal', label: 'Ma vue' },
            { value: 'general', label: 'Vue globale' },
          ]}
        />
        <div className="flex flex-wrap gap-2">
          {PERIODS.map((period) => (
            <button
              key={period.value}
              type="button"
              className={cn(
                'min-h-9 rounded-full px-3 text-xs font-semibold',
                url.period === period.value
                  ? 'bg-[#1B4FD8] text-white'
                  : 'bg-[#F4F1EA] text-[#1a1a1a]',
              )}
              onClick={() => replaceState({ ...url, period: period.value, anchorId: null })}
            >
              {period.label}
            </button>
          ))}
        </div>
        {url.period === 'custom' ? (
          <div className="flex gap-2">
            <input
              aria-label="Du"
              type="date"
              value={url.from}
              className="min-h-11 flex-1 rounded-lg border border-[#E8E6DF] px-2 text-sm"
              onChange={(event) => replaceState({ ...url, from: event.target.value, anchorId: null })}
            />
            <input
              aria-label="Au"
              type="date"
              value={url.to}
              className="min-h-11 flex-1 rounded-lg border border-[#E8E6DF] px-2 text-sm"
              onChange={(event) => replaceState({ ...url, to: event.target.value, anchorId: null })}
            />
          </div>
        ) : null}
        <div className="flex flex-wrap items-center gap-2">
          {statusOptions(url.kind).map((option) => (
            <button
              key={option.value}
              type="button"
              className={cn(
                'min-h-9 rounded-full px-3 text-xs font-semibold',
                url.status === option.value
                  ? 'bg-[#1a1a1a] text-white'
                  : 'bg-[#F4F1EA] text-[#1a1a1a]',
              )}
              onClick={() => replaceState({ ...url, status: option.value, anchorId: null })}
            >
              {option.label}
            </button>
          ))}
          {isDesktopWeb ? (
            <button
              type="button"
              className="ml-auto min-h-9 rounded-lg border border-[#E8E6DF] px-3 text-sm font-semibold"
              onClick={() => void refreshHistory()}
              disabled={list.isRefreshing || customIncomplete}
            >
              Actualiser
            </button>
          ) : null}
        </div>
      </div>
      <div
        ref={scrollRef}
        className="min-h-0 flex-1 overflow-y-auto overscroll-y-contain px-3 pb-4"
        {...pullToRefresh.pointerProps}
      >
        <FeedPullIndicator
          distance={pullToRefresh.pullDistance}
          refreshing={list.isRefreshing}
        />
        {undatedCount && undatedCount > 0 ? (
          <p className="pt-4 text-sm font-medium text-[#6b5f52]">
            {undatedCount} sans date
          </p>
        ) : null}
        {customIncomplete ? (
          <p className="pt-4 text-sm text-[#6b5f52]">Choisissez les deux dates.</p>
        ) : null}
        {list.isLoading && !customIncomplete ? (
          <div className="flex items-center justify-center py-16 text-[#7D7B75]">
            <LoaderCircle className="h-6 w-6 animate-spin" />
          </div>
        ) : null}
        {list.isError && items.length === 0 ? (
          <TerrainErrorState
            className="mt-4"
            message={resolveApiErrorMessage(
              list.error,
              HistoryApiError,
              "Impossible de charger l'historique.",
            )}
            onRetry={() => void refreshHistory()}
          />
        ) : null}
        {list.refreshError && items.length > 0 ? (
          <p className="pt-4 text-sm text-[#B5473D]">
            Actualisation impossible. Les données affichées sont conservées.
          </p>
        ) : null}
        {groups.map((group) => (
          <section key={group.key} className="mt-5 flex flex-col gap-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-[#7D7B75]">
              {group.label}
            </p>
            <div className="flex flex-col gap-2">
              {group.items.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  data-history-id={item.id}
                  className="rounded-xl border border-[#E8E6DF] bg-white px-4 py-3 text-left"
                  onClick={() => openItem(item.id)}
                >
                  <span className="block text-sm font-semibold text-[#1a1a1a]">{item.title}</span>
                  {source === 'cross' ? (
                    <span className="mt-0.5 block text-xs text-[#6b5f52]">{item.establishment_name}</span>
                  ) : null}
                  <span className="mt-1 block text-xs text-[#7D7B75]">
                    {originLabel(item.termination_origin, item.termination_actor_display_name)}
                  </span>
                </button>
              ))}
            </div>
          </section>
        ))}
        {!customIncomplete && !list.isLoading && !list.isError && items.length === 0 ? (
          <TerrainEmptyState
            className="mt-4"
            title="Aucun élément"
            description="Rien dans cette période pour le périmètre choisi."
          />
        ) : null}
        <div ref={loadMoreRef} />
        {list.isFetchingNextPage ? (
          <div className="flex justify-center py-4 text-[#7D7B75]">
            <LoaderCircle className="h-5 w-5 animate-spin" />
          </div>
        ) : null}
        {list.isFetchNextPageError ? (
          <div className="flex justify-center py-4">
            <button
              type="button"
              className="text-sm font-semibold text-[#1B4FD8]"
              onClick={() => void list.fetchNextPage()}
            >
              Réessayer le chargement
            </button>
          </div>
        ) : null}
        {stalled && !list.isFetchNextPageError ? (
          <div className="flex justify-center py-4">
            <button
              type="button"
              className="text-sm font-semibold text-[#1B4FD8]"
              onClick={() => void refreshHistory()}
            >
              Réessayer
            </button>
          </div>
        ) : null}
        {!customIncomplete &&
        !list.hasNextPage &&
        !stalled &&
        items.length > 0 &&
        !list.isError ? (
          <p className="py-4 text-center text-xs font-medium text-[#7D7B75]">Fin de l’historique</p>
        ) : null}
      </div>
    </div>
  )
}
