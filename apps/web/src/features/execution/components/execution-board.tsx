import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { TerrainErrorState } from '@/components/ui/terrain'
import { renderedItems } from '@/lib/feed-reading-window'
import {
  unwrapActionPlanExecutionFeedItems,
  type ActionPlanExecutionFeedCategory,
} from '@/features/action-plans/api'
import {
  useActionPlanExecutionFeedQuery,
  useCrossActionPlanExecutionFeedPinsQuery,
} from '@/features/action-plans/hooks'
import type { ActionPlanExecutionFeedSectionCounts } from '@/features/action-plans/types'
import type { ExecutionViewMode } from '../lib/types'
import { ExecutionBoardTransitionDialog } from './execution-board-transition-dialog'
import { resolveBoardCommand, type BoardTarget } from '../lib/execution-board-transition'
import type { ActionPlanExecutionFeedItem } from '@/features/action-plans/types'
import { ActionPlanExecutionFeedCard } from './action-plan-execution-feed-card'
import { useDesktopCalendarSurface } from '../lib/execution-calendar-surface'

const columns: Array<{
  category: ActionPlanExecutionFeedCategory
  title: string
  includeOverdue?: boolean
}> = [
  { category: 'in_progress', title: 'En cours', includeOverdue: true },
  { category: 'pending_validation', title: 'À valider' },
  { category: 'done', title: 'Terminés' },
]
const moveTargets: BoardTarget[] = ['in_progress', 'pending_validation', 'done', 'canceled']

type BoardProps = {
  establishmentId: string | null
  viewMode: ExecutionViewMode
  source: 'establishment' | 'cross'
  onOpenExecution: (id: string) => void
}
type BoardInteractions = {
  draggedId: string | null
  dragEnabled: boolean
  onDrag: (id: string | null) => void
  onMove: (id: string, target: BoardTarget) => void
}

function columnCount(
  category: ActionPlanExecutionFeedCategory,
  counts: ActionPlanExecutionFeedSectionCounts | null | undefined,
  includeOverdue: boolean,
): number | undefined {
  if (!counts || category === 'all') return undefined
  if (includeOverdue && category === 'in_progress') return counts.in_progress + counts.overdue
  return counts[category]
}

function moveOptions(item: ActionPlanExecutionFeedItem) {
  return moveTargets.flatMap((target) => {
    const command = resolveBoardCommand(item, target)
    if (!command) return []
    const label =
      command === 'markDone'
        ? item.requires_validation
          ? 'Envoyer en validation'
          : 'Terminer'
        : command === 'validate'
          ? 'Valider'
          : command === 'reopen'
            ? 'Rouvrir'
            : 'Annuler'
    return [{ target, label }]
  })
}

function BoardColumn({
  category,
  title,
  includeOverdue = false,
  establishmentId,
  viewMode,
  source,
  onOpenExecution,
  draggedId,
  dragEnabled,
  onDrag,
  onMove,
}: BoardProps & BoardInteractions & (typeof columns)[number]) {
  const query = useActionPlanExecutionFeedQuery(establishmentId, viewMode, {
    category,
    source,
    includeOverdue,
  })
  const crossPins = useCrossActionPlanExecutionFeedPinsQuery(viewMode, category, {
    enabled: source === 'cross',
    includeOverdue,
  })
  const pinned =
    source === 'cross'
      ? crossPins.data
        ? renderedItems(crossPins.data.window, (item) => item.action_plan_execution.id)
        : []
      : (query.data?.pins ?? [])
  const ordinary = query.data
    ? unwrapActionPlanExecutionFeedItems(
        renderedItems(query.data.window, (item) => item.action_plan_execution.id),
      )
    : []
  const items = [
    ...new Map(
      [...unwrapActionPlanExecutionFeedItems(pinned), ...ordinary].map((item) => [item.id, item]),
    ).values(),
  ]
  const count = columnCount(category, query.data?.sectionCounts, includeOverdue)
  const canDrop = dragEnabled && category !== 'all'
  return (
    <section
      onDragOver={(event) => {
        if (draggedId && canDrop) event.preventDefault()
      }}
      onDrop={(event) => {
        event.preventDefault()
        if (draggedId && canDrop) onMove(draggedId, category as BoardTarget)
        onDrag(null)
      }}
      aria-label={title}
      className="flex w-80 shrink-0 flex-col gap-3 rounded-2xl border border-[#E8E6DF] bg-[#F5F4F0] p-3"
    >
      <div className="flex items-center justify-between gap-2">
        <h2 className="font-semibold text-[#1a1a1a]">
          {title}
          {count != null ? ` · ${count}` : ''}
        </h2>
        <button
          type="button"
          className="min-h-10 text-xs font-medium text-[#114660]"
          disabled={query.isRefreshing}
          onClick={() => {
            void query.refresh()
            if (source === 'cross') void crossPins.refetch()
          }}
        >
          Actualiser
        </button>
      </div>
      {query.isLoading && (
        <p role="status" className="text-sm">
          Chargement…
        </p>
      )}
      {query.isError || query.refreshError ? (
        <TerrainErrorState message="Chargement impossible." onRetry={() => void query.refresh()} />
      ) : null}
      {source === 'cross' && crossPins.isLoading && <p role="status">Chargement des épinglés…</p>}
      {source === 'cross' && crossPins.isError && (
        <TerrainErrorState
          message="Les épinglés n’ont pas pu être chargés."
          onRetry={() => void crossPins.refetch()}
        />
      )}
      {!query.isLoading &&
        !query.isError &&
        !(source === 'cross' && (crossPins.isLoading || crossPins.isError)) &&
        items.length === 0 && <p className="text-sm text-[#42433F]">Aucun plan.</p>}
      {query.data?.window.behindCursor && (
        <Button
          variant="outline"
          onClick={() => void query.loadBehind()}
          disabled={query.isLoadingMore}
        >
          Plans précédents
        </Button>
      )}
      {items.map((item) => {
        const options = source === 'cross' ? [] : moveOptions(item)
        const overdue = item.status === 'in_progress' && item.is_overdue
        return (
          <div
            key={item.id}
            draggable={dragEnabled && options.length > 0}
            onDragStart={(event) => {
              if (!dragEnabled || options.length === 0) {
                event.preventDefault()
                return
              }
              onDrag(item.id)
              event.dataTransfer.setData('text/plain', item.id)
              event.dataTransfer.effectAllowed = 'move'
            }}
            onDragEnd={() => onDrag(null)}
          >
            {overdue ? (
              <span className="mb-1 inline-flex rounded-full bg-[#F8E6E4] px-2 py-0.5 text-xs font-semibold text-[#A32620]">
                En retard
              </span>
            ) : null}
            <ActionPlanExecutionFeedCard item={item} onSelect={onOpenExecution} />
            {options.length > 0 && (
              <select
                aria-label={`Changer l’état de ${item.title}`}
                value=""
                className="mt-1 min-h-10 w-full rounded-lg border bg-white px-2 text-sm text-[#1a1a1a]"
                onChange={(event) => onMove(item.id, event.target.value as BoardTarget)}
              >
                <option value="">Changer l’état…</option>
                {options.map((option) => (
                  <option key={option.target} value={option.target}>
                    {option.label}
                  </option>
                ))}
              </select>
            )}
          </div>
        )
      })}
      {source === 'cross' && crossPins.continuationError && (
        <TerrainErrorState
          message="La suite des épinglés n’a pas pu être chargée."
          onRetry={() => void crossPins.retryStalledContinuation()}
        />
      )}
      {source === 'cross' && crossPins.hasNextPage && (
        <Button
          variant="outline"
          disabled={crossPins.isFetchingNextPage}
          onClick={() => void crossPins.fetchNextPage()}
        >
          Autres plans épinglés
        </Button>
      )}
      {query.continuationError ? (
        <TerrainErrorState
          message="La suite n’a pas pu être chargée."
          onRetry={() => void query.retryStalledContinuation()}
        />
      ) : null}
      {query.hasNextPage && (
        <Button
          variant="outline"
          disabled={query.isLoadingMore}
          onClick={() => void query.loadMore()}
        >
          {query.isLoadingMore ? 'Chargement…' : 'Voir la suite'}
        </Button>
      )}
    </section>
  )
}

export function ExecutionBoard(props: BoardProps) {
  const computer = useDesktopCalendarSurface()
  const dragEnabled = computer && props.source !== 'cross'
  const [draggedId, setDraggedId] = useState<string | null>(null)
  const [move, setMove] = useState<{ id: string; target: BoardTarget } | null>(null)
  const interactions = {
    draggedId,
    dragEnabled,
    onDrag: setDraggedId,
    onMove: (id: string, target: BoardTarget) => setMove({ id, target }),
  }
  const [showCanceled, setShowCanceled] = useState(false)
  return (
    <div className="flex min-h-0 flex-1 flex-col gap-3 py-3">
      {move && props.establishmentId && props.source !== 'cross' && (
        <ExecutionBoardTransitionDialog
          key={`${move.id}:${move.target}`}
          establishmentId={props.establishmentId}
          executionId={move.id}
          target={move.target}
          onClose={() => setMove(null)}
          onOpenExecution={props.onOpenExecution}
        />
      )}
      <div className="flex flex-wrap items-center justify-between gap-2 px-3">
        <p className="text-sm text-[#42433F]">
          {dragEnabled
            ? 'Ouvrez un plan pour ses tâches. Les changements d’état, par glisser-déposer ou menu, demandent confirmation. Le retard s’affiche sur la carte.'
            : 'Ouvrez un plan pour ses tâches. Sur mobile et tablette tactile, changez l’état depuis le menu de la carte. Le retard s’affiche sur la carte.'}
        </p>
        <Button
          variant="outline"
          aria-pressed={showCanceled}
          onClick={() => setShowCanceled(!showCanceled)}
        >
          {showCanceled ? 'Masquer les annulés' : 'Voir les annulés'}
        </Button>
      </div>
      <div className="flex items-start gap-3 overflow-x-auto px-3 pb-4">
        {columns.map((column) => (
          <BoardColumn key={column.category} {...props} {...interactions} {...column} />
        ))}
        {showCanceled && (
          <BoardColumn {...props} {...interactions} category="canceled" title="Annulés" />
        )}
      </div>
    </div>
  )
}
