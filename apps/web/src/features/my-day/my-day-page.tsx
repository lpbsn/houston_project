import { useInfiniteQuery } from '@tanstack/react-query'
import { ArrowRight, Bell, Clock, MessageCircle, Plus, RefreshCw, Sun } from 'lucide-react'

import { TerrainCard } from '@/components/ui/terrain'
import { Button } from '@/components/ui/button'
import { NotificationRow } from '@/features/notifications/components/notification-row'
import { useNotificationSelection, useNotificationsInfiniteQuery } from '@/features/notifications/hooks'

import { fetchMyDay, myDayQueryKey, type MyDayTask } from './api'

const sections: { key: MyDayTask['bucket']; title: string; description: string }[] = [
  { key: 'overdue', title: 'En retard', description: 'À reprendre en priorité.' },
  { key: 'today', title: 'Aujourd’hui', description: 'Les échéances de votre journée.' },
  { key: 'upcoming', title: 'À venir', description: 'Pour anticiper la suite.' },
  { key: 'undated', title: 'Sans échéance', description: 'Du travail à planifier avec votre équipe.' },
]

export function formatTaskDeadline(task: MyDayTask, timeZone: string) {
  if (!task.due_at) return 'Sans échéance'
  return new Intl.DateTimeFormat('fr-FR', {
    day: 'numeric', month: 'short', timeZone,
    ...(!task.all_day ? { hour: '2-digit', minute: '2-digit' } as const : {}),
  }).format(new Date(task.due_at))
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
  if (!establishmentId) return <p className="p-4">Sélectionnez un établissement.</p>

  const tasks = query.data?.pages.flatMap(page => page.items) ?? []
  const timeZone = query.data?.pages[0]?.timezone ?? 'Europe/Paris'
  const latest = notifications.data?.pages.flatMap(page => page.items).slice(0, 5) ?? []
  const base = `/e/${establishmentId}`

  return (
    <div className="mx-auto w-full max-w-6xl space-y-6 p-4 text-[#1A1A1A] sm:p-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="mb-2 flex items-center gap-2 text-sm font-medium text-[#114660]">
            <Sun className="h-4 w-4" />
            {new Intl.DateTimeFormat('fr-FR', { weekday: 'long', day: 'numeric', month: 'long', timeZone }).format(new Date())}
          </div>
          <h1 className="text-2xl font-semibold">Ma journée</h1>
          <p className="mt-1 text-sm text-[#4A4A45]">Votre travail, vos priorités et les dernières nouvelles.</p>
        </div>
        <Button onClick={() => onNavigate(`${base}/reporting`)}><Plus className="h-4 w-4" />Partager une observation</Button>
      </header>

      <div className="grid items-start gap-6 xl:grid-cols-[minmax(0,2fr)_minmax(280px,1fr)]">
        <div className="space-y-6">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-lg font-semibold">Mon travail</h2>
            <Button variant="outline" onClick={() => onNavigate(`${base}/execution`)}>Tous mes plans<ArrowRight className="h-4 w-4" /></Button>
          </div>
          <p className="text-sm text-[#4A4A45]">Vos tâches attribuées et le travail partagé de votre pôle. Ouvrez le plan pour agir ou échanger.</p>
          {query.isPending && <p role="status">Chargement de votre journée…</p>}
          {query.isError && <TerrainCard><p role="alert">Impossible de charger votre travail.</p><Button variant="outline" className="mt-3" onClick={() => void query.refetch()}><RefreshCw className="h-4 w-4" />Réessayer</Button></TerrainCard>}
          {!query.isPending && !query.isError && tasks.length === 0 && (
            <TerrainCard><h3 className="font-semibold">Aucune tâche à traiter.</h3><p className="mt-2 text-sm text-[#4A4A45]">Consultez vos plans pour retrouver ceux sans tâches ou en attente de validation.</p></TerrainCard>
          )}
          {!query.isError && sections.map(section => {
            const rows = tasks.filter(task => task.bucket === section.key)
            if (!rows.length) return null
            return <section key={section.key} className="space-y-3">
              <h3 className={`font-semibold ${section.key === 'overdue' ? 'text-[#A32620]' : 'text-[#1A1A1A]'}`}>{section.title}</h3>
              <p className="text-sm text-[#4A4A45]">{section.description}</p>
              {rows.map(task => <TerrainCard key={task.id} className={section.key === 'overdue' ? 'border-l-4 border-l-[#A32620]' : ''}>
                <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                  <span className="rounded-md bg-[#E8E6DF] px-2 py-1 font-semibold">{task.pole}</span>
                  <span className={section.key === 'overdue' ? 'font-semibold text-[#A32620]' : 'text-[#4A4A45]'}><Clock className="mr-1 inline h-3 w-3" />{formatTaskDeadline(task, timeZone)}</span>
                </div>
                <h4 className="mt-3 font-semibold">{task.title}</h4>
                <p className="mt-1 text-sm text-[#4A4A45]">{task.execution_title}</p>
                <div className="mt-4 flex flex-wrap items-center justify-between gap-2 border-t border-[#E8E6DF] pt-3">
                  <span className="text-xs font-medium text-[#114660]">{task.shared ? 'À partager avec mon pôle' : 'Attribuée à moi'}</span>
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" aria-label={`Discuter : ${task.title}`} onClick={() => onNavigate(`${base}/execution/${task.execution_id}?tab=comments`)}><MessageCircle className="h-4 w-4" />Discuter</Button>
                    <Button size="sm" onClick={() => onNavigate(`${base}/execution/${task.execution_id}`)}>Ouvrir le plan<ArrowRight className="h-4 w-4" /></Button>
                  </div>
                </div>
              </TerrainCard>)}
            </section>
          })}
          {query.hasNextPage && !query.isError && <Button variant="outline" disabled={query.isFetchingNextPage} onClick={() => void query.fetchNextPage()}>{query.isFetchingNextPage ? 'Chargement…' : 'Afficher la suite'}</Button>}
        </div>
        <aside className="space-y-3">
          <h2 className="flex items-center gap-2 text-lg font-semibold"><Bell className="h-5 w-5 text-[#114660]" />Les dernières nouvelles</h2>
          <p className="text-sm text-[#4A4A45]">Actions, résolutions et échanges : retrouvez les suites qui vous concernent.</p>
          {notifications.isPending && <p role="status">Chargement des notifications…</p>}
          {notifications.isError && <p role="alert">Les notifications sont momentanément indisponibles.</p>}
          {!notifications.isPending && !notifications.isError && latest.length === 0 && <TerrainCard>Aucune notification pour le moment.</TerrainCard>}
          {latest.map(notification => <NotificationRow key={notification.id} notification={notification} onSelect={handleSelectNotification} />)}
          <Button variant="outline" onClick={() => onNavigate('/notifications-center')}>Toutes les notifications<ArrowRight className="h-4 w-4" /></Button>
        </aside>
      </div>
    </div>
  )
}
