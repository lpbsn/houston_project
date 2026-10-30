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
import type { ExecutionViewMode } from '../lib/types'
import { ExecutionBoardTransitionDialog } from './execution-board-transition-dialog'
import type { BoardTarget } from '../lib/execution-board-transition'
import type { ActionPlanExecutionFeedItem } from '@/features/action-plans/types'
import { ActionPlanExecutionFeedCard } from './action-plan-execution-feed-card'

const columns: Array<{ category: ActionPlanExecutionFeedCategory; title: string }> = [
  { category: 'overdue', title: 'En retard' },
  { category: 'in_progress', title: 'En cours' },
  { category: 'pending_validation', title: 'À valider' },
  { category: 'done', title: 'Terminés' },
]
type BoardProps = {
  establishmentId: string | null
  viewMode: ExecutionViewMode
  source: 'establishment' | 'cross'
  onOpenExecution: (id: string) => void
}
type BoardInteractions = {
  draggedId: string | null
  onDrag: (id: string | null) => void
  onMove: (id: string, target: BoardTarget) => void
}

function BoardColumn({
  category,
  title,
  establishmentId,
  viewMode,
  source,
  onOpenExecution,
  draggedId,
  onDrag,
  onMove,
}: BoardProps & BoardInteractions & (typeof columns)[number]) {
  // Each column uses the existing bounded cursor feed; never fetch all plans.
  const query = useActionPlanExecutionFeedQuery(establishmentId, viewMode, { category, source })
  const crossPins = useCrossActionPlanExecutionFeedPinsQuery(viewMode, category, {
    enabled: source === 'cross',
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
  const count = category === 'all' ? undefined : query.data?.sectionCounts?.[category]
  return (
    <section
      onDragOver={(event) => {
        if (draggedId && source !== 'cross' && category !== 'overdue') event.preventDefault()
      }}
      onDrop={(event) => {
        event.preventDefault()
        if (draggedId && source !== 'cross' && category !== 'overdue' && category !== 'all')
          onMove(draggedId, category)
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
      {items.map((item) => (
        <div
          key={item.id}
          draggable={source !== 'cross' && canMoveItem(item)}
          onDragStart={(event) => {
            onDrag(item.id)
            event.dataTransfer.setData('text/plain', item.id)
            event.dataTransfer.effectAllowed = 'move'
          }}
          onDragEnd={() => onDrag(null)}
        >
          <ActionPlanExecutionFeedCard item={item} onSelect={onOpenExecution} />
          {source !== 'cross' && canMoveItem(item) && (
            <select
              aria-label={`Changer l’état de ${item.title}`}
              value=""
              className="mt-1 min-h-10 w-full rounded-lg border bg-white px-2 text-sm text-[#1a1a1a]"
              onChange={(event) => onMove(item.id, event.target.value as BoardTarget)}
            >
              <option value="">Changer l’état…</option>
              {item.permission_hints.can_mark_done && (
                <option value={item.requires_validation ? 'pending_validation' : 'done'}>
                  {item.requires_validation ? 'Envoyer en validation' : 'Terminer'}
                </option>
              )}
              {item.permission_hints.can_validate && <option value="done">Valider</option>}
              {item.permission_hints.can_reopen && <option value="in_progress">Rouvrir</option>}
              {item.permission_hints.can_cancel && <option value="canceled">Annuler</option>}
            </select>
          )}
        </div>
      ))}
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

function canMoveItem(item: ActionPlanExecutionFeedItem) {
  const hints = item.permission_hints
  return Boolean(
    hints?.can_mark_done || hints?.can_validate || hints?.can_reopen || hints?.can_cancel,
  )
}

export function ExecutionBoard(props: BoardProps) {
  const [draggedId, setDraggedId] = useState<string | null>(null)
  const [move, setMove] = useState<{ id: string; target: BoardTarget } | null>(null)
  const interactions = {
    draggedId,
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
          Ouvrez un plan pour ses tâches. Les changements d’état, par glisser-déposer ou menu,
          demandent confirmation. Le retard dépend de l’échéance.
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
