import { useInfiniteQuery } from '@tanstack/react-query'
import { ArrowRight, ChevronRight, Plus, Sun } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { TerrainEmptyState, TerrainErrorState } from '@/components/ui/terrain'
import { useNotificationSelection, useNotificationsInfiniteQuery } from '@/features/notifications/hooks'
import { formatNotificationRelativeTime } from '@/features/notifications/lib/notification-display'
import type { NotificationItem } from '@/features/notifications/types'
import { terrain, terrainCardClassName, terrainSectionDotVariants } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

import { fetchMyDay, myDayQueryKey, type MyDayTask } from './api'

const sections: {
  key: MyDayTask['bucket']
  title: string
  dot?: keyof typeof terrainSectionDotVariants
}[] = [
  { key: 'overdue', title: 'En retard', dot: 'danger' },
  { key: 'today', title: 'Aujourd’hui', dot: 'success' },
  { key: 'upcoming', title: 'À venir' },
  { key: 'undated', title: 'Sans échéance' },
]

const textNavClassName = cn(
  'inline-flex min-h-11 items-center gap-1 rounded-sm text-sm font-medium outline-none focus-visible:ring-2 focus-visible:ring-[#1B4FD8]/40',
  terrain.primary,
)

type CivilDay = {
  year: number
  month: number
  day: number
}

function civilDay(date: Date, timeZone: string): CivilDay | null {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).formatToParts(date)
  const read = (type: Intl.DateTimeFormatPartTypes) =>
    Number(parts.find((part) => part.type === type)?.value)
  const year = read('year')
  const month = read('month')
  const day = read('day')
  if (!Number.isInteger(year) || !Number.isInteger(month) || !Number.isInteger(day)) return null
  return { year, month, day }
}

function sameCivilDay(left: CivilDay, right: CivilDay): boolean {
  return left.year === right.year && left.month === right.month && left.day === right.day
}

function shiftCivilDay(day: CivilDay, days: number): CivilDay {
  const shifted = new Date(Date.UTC(day.year, day.month - 1, day.day + days))
  return {
    year: shifted.getUTCFullYear(),
    month: shifted.getUTCMonth() + 1,
    day: shifted.getUTCDate(),
  }
}

function formatClock(date: Date, timeZone: string): string {
  return new Intl.DateTimeFormat('fr-FR', {
    hour: '2-digit',
    minute: '2-digit',
    timeZone,
  }).format(date)
}

function formatDayMonth(date: Date, timeZone: string, day: CivilDay, today: CivilDay): string {
  return new Intl.DateTimeFormat('fr-FR', {
    day: 'numeric',
    month: 'short',
    timeZone,
    ...(day.year === today.year ? {} : { year: 'numeric' }),
  }).format(date)
}

export function formatMyDayHeadingDate(timeZone: string, now = new Date()): string {
  return new Intl.DateTimeFormat('fr-FR', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    timeZone,
  }).format(now)
}

export function formatTaskDeadline(
  task: MyDayTask,
  timeZone: string,
  now = new Date(),
): string | null {
  if (!task.due_at) return null
  const due = new Date(task.due_at)
  if (Number.isNaN(due.getTime())) return null

  const dueDay = civilDay(due, timeZone)
  const today = civilDay(now, timeZone)
  if (!dueDay || !today) return null
  if (sameCivilDay(dueDay, today)) {
    return task.all_day ? null : formatClock(due, timeZone)
  }
  if (sameCivilDay(dueDay, shiftCivilDay(today, -1))) {
    return task.all_day ? 'Hier' : `Hier, ${formatClock(due, timeZone)}`
  }

  const day = formatDayMonth(due, timeZone, dueDay, today)
  return task.all_day ? day : `${day}, ${formatClock(due, timeZone)}`
}

function attributionLabel(shared: boolean): 'Pour moi' | 'Équipe' {
  // `shared` is unassigned work in the member's poles, not an assignment to everyone.
  return shared ? 'Équipe' : 'Pour moi'
}

type WorkColumnProps = {
  tasks: MyDayTask[]
  timeZone: string | undefined
  isPending: boolean
  isError: boolean
  isRefetchError: boolean
  isFetchNextPageError: boolean
  isFetchingNextPage: boolean
  hasNextPage: boolean
  onRetry: () => void
  onLoadMore: () => void
  onOpen: (task: MyDayTask) => void
  onSeePlans: () => void
}

function WorkColumn({
  tasks,
  timeZone,
  isPending,
  isError,
  isRefetchError,
  isFetchNextPageError,
  isFetchingNextPage,
  hasNextPage,
  onRetry,
  onLoadMore,
  onOpen,
  onSeePlans,
}: WorkColumnProps) {
  const showGroups = tasks.length > 0

  return (
    <section className="min-w-0 space-y-4">
      <div>
        <h2 className="text-lg font-semibold">À traiter</h2>
        <p className={cn('mt-1 text-sm', terrain.muted)}>
          Vos tâches personnelles et le travail de vos pôles.
        </p>
      </div>

      {isPending ? <p role="status">Chargement de votre journée…</p> : null}
      {isError && !showGroups ? (
        <TerrainErrorState message="Impossible de charger votre travail." onRetry={onRetry} />
      ) : null}
      {!isPending && !isError && !showGroups ? (
        <TerrainEmptyState title="Aucune tâche à traiter pour le moment." />
      ) : null}

      {showGroups ? (
        <div className="space-y-5">
          {sections.map((section) => {
            const rows = tasks.filter((task) => task.bucket === section.key)
            if (rows.length === 0) return null
            return (
              <section key={section.key}>
                <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold">
                  {section.dot ? (
                    <span
                      className={cn('size-2 shrink-0 rounded-full', terrainSectionDotVariants[section.dot])}
                      aria-hidden
                    />
                  ) : null}
                  {section.title}
                </h3>
                <div className={terrainCardClassName()}>
                  <ul className="divide-y divide-[#E8E6DF]">
                    {rows.map((task) => {
                      const deadline = timeZone ? formatTaskDeadline(task, timeZone) : null
                      return (
                        <li key={task.id} className="@container/task">
                          <button
                            type="button"
                            className="flex min-h-11 w-full items-center gap-3 px-4 py-3 text-left outline-none hover:bg-[#F5F4F0] focus-visible:ring-2 focus-visible:ring-[#1B4FD8]/40 focus-visible:ring-inset"
                            onClick={() => onOpen(task)}
                          >
                            <div className="flex min-w-0 flex-1 flex-col gap-2 @min-[32rem]/task:flex-row @min-[32rem]/task:items-start @min-[32rem]/task:justify-between @min-[32rem]/task:gap-4">
                              <div className="min-w-0 flex-1">
                                <p className="font-semibold break-words">{task.title}</p>
                                <p className={cn('mt-0.5 text-sm break-words', terrain.muted)}>
                                  {task.pole} · {task.execution_title}
                                </p>
                              </div>
                              <div className="flex shrink-0 flex-col items-start gap-1 @min-[32rem]/task:items-end">
                                {deadline ? (
                                  <p className={cn(
                                    'text-sm',
                                    task.bucket === 'overdue' ? cn('font-medium', terrain.danger) : terrain.muted,
                                  )}
                                  >
                                    {deadline}
                                  </p>
                                ) : null}
                                <span className={cn(
                                  'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium',
                                  task.shared ? 'bg-[#E8E6DF] text-[#555]' : terrain.transcript,
                                )}
                                >
                                  {attributionLabel(task.shared)}
                                </span>
                              </div>
                            </div>
                            <ChevronRight className="size-4 shrink-0 text-[#a3a19a]" aria-hidden />
                          </button>
                        </li>
                      )
                    })}
                  </ul>
                </div>
              </section>
            )
          })}
        </div>
      ) : null}

      {isFetchNextPageError ? (
        <p role="alert" className={cn('text-sm', terrain.danger)}>Impossible de charger la suite.</p>
      ) : null}
      {isRefetchError ? (
        <TerrainErrorState message="Impossible d’actualiser votre travail." onRetry={onRetry} />
      ) : null}
      {hasNextPage || isFetchNextPageError ? (
        <Button type="button" variant="outline" disabled={isFetchingNextPage} onClick={onLoadMore}>
          {isFetchingNextPage ? 'Chargement…' : 'Afficher la suite'}
        </Button>
      ) : null}
      <button type="button" className={textNavClassName} onClick={onSeePlans}>
        Voir tous les plans d’exécution
        <ArrowRight className="size-4" aria-hidden />
      </button>
    </section>
  )
}

type NewsPanelProps = {
  items: NotificationItem[]
  isPending: boolean
  isError: boolean
  onRetry: () => void
  onSelect: (notification: NotificationItem) => void
  onSeeAll: () => void
}

function NewsPanel({ items, isPending, isError, onRetry, onSelect, onSeeAll }: NewsPanelProps) {
  const hasItems = items.length > 0

  return (
    <aside className="min-w-0 space-y-3">
      <div>
        <h2 className="text-lg font-semibold">Dernières nouvelles</h2>
        <p className={cn('mt-1 text-sm', terrain.muted)}>Ce qui vous concerne</p>
      </div>
      <div className={terrainCardClassName()}>
        {isPending && !hasItems ? (
          <p role="status" className={cn('px-4 py-3 text-sm', terrain.muted)}>
            Chargement des notifications…
          </p>
        ) : null}
        {isError && !hasItems ? (
          <div className="px-4 py-3" role="alert">
            <p className="text-sm">Les notifications sont momentanément indisponibles.</p>
            <Button type="button" variant="outline" className="mt-3" onClick={onRetry}>
              Réessayer
            </Button>
          </div>
        ) : null}
        {!isPending && !isError && !hasItems ? (
          <p className={cn('px-4 py-3 text-sm', terrain.muted)}>Aucune notification pour le moment.</p>
        ) : null}
        {hasItems ? (
          <ul className="divide-y divide-[#E8E6DF]">
            {items.map((notification) => {
              const isUnread = notification.status === 'unread'
              return (
                <li key={notification.id}>
                  <button
                    type="button"
                    className="w-full px-4 py-3 text-left outline-none focus-visible:ring-2 focus-visible:ring-[#1B4FD8]/40 focus-visible:ring-inset"
                    onClick={() => onSelect(notification)}
                  >
                    <span className="relative block pl-4">
                      {isUnread ? (
                        <span className="absolute top-1.5 left-0 size-2 rounded-full bg-[#1B4FD8]" aria-hidden />
                      ) : null}
                      <span className="block font-semibold break-words">{notification.title}</span>
                      {notification.body ? (
                        <span className={cn('mt-0.5 block line-clamp-2 text-sm', terrain.muted)}>
                          {notification.body}
                        </span>
                      ) : null}
                      <span className={cn('mt-1 block text-xs', terrain.muted)}>
                        {formatNotificationRelativeTime(notification.created_at)}
                        {notification.priority === 'urgent' ? ' · Urgent' : null}
                        {isUnread ? <span className="sr-only"> Non lu</span> : null}
                      </span>
                    </span>
                  </button>
                </li>
              )
            })}
          </ul>
        ) : null}
        {isError && hasItems ? (
          <div className="border-t border-[#E8E6DF] px-4 py-3" role="alert">
            <p className="text-sm">Les notifications sont momentanément indisponibles.</p>
            <Button type="button" variant="outline" className="mt-3" onClick={onRetry}>
              Réessayer
            </Button>
          </div>
        ) : null}
        <div className="border-t border-[#E8E6DF] px-4">
          <button type="button" className={textNavClassName} onClick={onSeeAll}>
            Voir toutes les notifications
            <ArrowRight className="size-4" aria-hidden />
          </button>
        </div>
      </div>
    </aside>
  )
}

export function MyDayPage({ establishmentId, onNavigate }: {
  establishmentId: string | null
  onNavigate: (path: string) => void
}) {
  const query = useInfiniteQuery({
    queryKey: myDayQueryKey(establishmentId),
    initialPageParam: 0,
    queryFn: ({ pageParam }) => fetchMyDay(establishmentId!, pageParam),
    getNextPageParam: (page) => page.next_offset ?? undefined,
    enabled: Boolean(establishmentId),
    // Refresh dates at midnight and recover when realtime is temporarily unavailable.
    refetchInterval: 60_000,
  })
  const notifications = useNotificationsInfiniteQuery(establishmentId)
  const { handleSelectNotification } = useNotificationSelection(establishmentId, { onNavigate })

  if (!establishmentId) {
    return <p className="p-4 text-sm text-[#1a1a1a]">Sélectionnez un établissement.</p>
  }

  const tasks = query.data?.pages.flatMap((page) => page.items) ?? []
  const timeZone = query.data?.pages[0]?.timezone
  const latest = notifications.data?.pages.flatMap((page) => page.items).slice(0, 5) ?? []
  const base = `/e/${establishmentId}`

  return (
    <div className="@container/day mx-auto w-full min-w-0 max-w-6xl">
      <div className={cn('space-y-6 p-4 @min-[960px]/day:p-6', terrain.foreground)}>
        <header className="flex flex-col gap-4 @min-[40rem]/day:flex-row @min-[40rem]/day:items-start @min-[40rem]/day:justify-between">
          <div>
            {timeZone ? (
              <p className={cn(
                'mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.06em]',
                terrain.muted,
              )}
              >
                <Sun className={cn('size-3.5', terrain.amber)} aria-hidden />
                {formatMyDayHeadingDate(timeZone)}
              </p>
            ) : null}
            <h1 className="text-2xl font-semibold tracking-tight @min-[960px]/day:text-[1.75rem]">
              Votre travail, en un coup d’œil.
            </h1>
          </div>
          <Button
            type="button"
            className="h-11 self-start rounded-full px-4"
            onClick={() => onNavigate(`${base}/reporting`)}
          >
            <Plus />
            Partager une observation
          </Button>
        </header>

        {/* Container query, not a viewport breakpoint: native keeps a max-w-md shell on large screens. */}
        <div className="grid items-start gap-6 @min-[960px]/day:grid-cols-[minmax(0,2fr)_minmax(18rem,1fr)]">
          <WorkColumn
            tasks={tasks}
            timeZone={timeZone}
            isPending={query.isPending}
            isError={query.isError}
            isRefetchError={query.isRefetchError}
            isFetchNextPageError={query.isFetchNextPageError}
            isFetchingNextPage={query.isFetchingNextPage}
            hasNextPage={Boolean(query.hasNextPage)}
            onRetry={() => void query.refetch()}
            onLoadMore={() => void query.fetchNextPage()}
            onOpen={(task) => onNavigate(`${base}/execution/${task.execution_id}`)}
            onSeePlans={() => onNavigate(`${base}/execution`)}
          />
          <NewsPanel
            items={latest}
            isPending={notifications.isPending}
            isError={notifications.isError}
            onRetry={() => void notifications.refetch()}
            onSelect={handleSelectNotification}
            onSeeAll={() => onNavigate('/notifications-center')}
          />
        </div>
      </div>
    </div>
  )
}
