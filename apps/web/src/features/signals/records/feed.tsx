import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query'
import { useState } from 'react'
import {
  ArrowRight,
  CalendarDays,
  GripVertical,
  Plus,
  RefreshCw,
} from 'lucide-react'
import { useAuth } from '@/app/auth-provider'
import { BusinessUnitBadge } from '@/components/ui/terrain/business-unit-badge'
import { Button } from '@/components/ui/button'
import { TerrainDialog } from '@/components/ui/terrain/terrain-dialog'
import { isDesktopWebLanding } from '@/features/auth/lib/authenticated-landing'
import { useLgViewport } from '@/lib/lg-viewport'
import {
  createRecord,
  getRecord,
  listRecords,
  recordKeys,
  recordOptions,
  updateRecord,
  type FieldRecord,
  type RecordFilters,
  type RecordStage,
} from './api'
import {
  CloseRecordDialog,
  dateLabel,
  ErrorNote,
  inputClass,
  panelClass,
  stages,
} from './shared'
import { monthWindow, RecordCalendar } from './calendar'

function RecordCard({
  record,
  onOpen,
  onMove,
}: {
  record: FieldRecord
  onOpen: (id: string) => void
  onMove: (record: FieldRecord, stage: RecordStage) => void
}) {
  return (
    <article
      className={`${panelClass} p-4`}
      draggable={record.can_manage}
      onDragStart={(e) =>
        e.dataTransfer.setData(
          'application/spore-record',
          JSON.stringify({ id: record.id, updated_at: record.updated_at }),
        )
      }
    >
      <div className="mb-2 flex items-center justify-between gap-2">
        <BusinessUnitBadge colorIndex={record.color_index}>
          {record.pole}
        </BusinessUnitBadge>
        {record.is_pinned && (
          <span className="text-xs font-semibold">Épinglée</span>
        )}
        {record.can_manage && (
          <GripVertical size={15} aria-label="Déplacer la fiche" />
        )}
      </div>
      <button
        className="block w-full text-left text-base font-semibold leading-snug hover:underline"
        onClick={() => onOpen(record.id)}
      >
        {record.title}
      </button>
      <p className="mt-2 text-xs text-[#45564A]">
        {record.owner?.name ?? 'Responsable à définir'} ·{' '}
        {record.observation_count} observation
        {record.observation_count > 1 ? 's' : ''}
      </p>
      {record.due_on && (
        <p
          className={`mt-2 flex items-center gap-1 text-xs font-semibold ${record.calendar?.overdue ? 'text-[#A02416]' : 'text-[#294733]'}`}
        >
          <CalendarDays size={13} />
          {dateLabel(record.due_on)}
        </p>
      )}
      {record.blocked_reason && (
        <p className="mt-2 rounded-lg bg-[#FFF0CF] p-2 text-xs text-[#633900]">
          Bloqué · {record.blocked_reason}
        </p>
      )}
      {record.can_progress && (
        <select
          aria-label={`Étape de ${record.title}`}
          className={`${inputClass} mt-3 py-2`}
          value={record.stage}
          onChange={(e) => onMove(record, e.target.value as RecordStage)}
        >
          {stages
            .filter(
              (stage) =>
                record.can_manage ||
                ['doing', 'review'].includes(stage.id) ||
                stage.id === record.stage,
            )
            .map((stage) => (
              <option key={stage.id} value={stage.id}>
                {stage.label}
              </option>
            ))}
        </select>
      )}
    </article>
  )
}
function CreateRecord({
  site,
  onClose,
  onCreated,
}: {
  site: string
  onClose: () => void
  onCreated: (id: string) => void
}) {
  const [title, setTitle] = useState('')
  const [pole, setPole] = useState('')
  const options = useQuery({
    queryKey: ['field-record-options', site],
    queryFn: () => recordOptions(site),
  })
  const mutation = useMutation({
    mutationFn: () => createRecord(site, { title, business_unit_id: pole }),
    onSuccess: (record) => onCreated(record.id),
  })
  return (
    <TerrainDialog
      title="Créer une fiche"
      description="Un sujet à organiser, même sans observation ni tâche."
      open
      onClose={onClose}
    >
      <form
        className="grid gap-4"
        onSubmit={(e) => {
          e.preventDefault()
          mutation.mutate()
        }}
      >
        <label className="grid gap-2 text-sm">
          Titre
          <input
            required
            maxLength={200}
            className={inputClass}
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
        </label>
        <label className="grid gap-2 text-sm">
          Pôle
          <select
            required
            className={inputClass}
            value={pole}
            onChange={(e) => setPole(e.target.value)}
          >
            <option value="">Choisir un pôle</option>
            {options.data?.poles.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </label>
        <ErrorNote error={mutation.error ?? options.error} />
        <Button
          disabled={mutation.isPending || !pole || !title.trim()}
          type="submit"
        >
          Créer la fiche
        </Button>
      </form>
    </TerrainDialog>
  )
}
function RecordsPane({
  site,
  filters,
  onOpen,
  onMove,
  month,
  calendar = false,
}: {
  site: string
  filters: RecordFilters
  onOpen: (id: string) => void
  onMove: (record: FieldRecord, stage: RecordStage) => void
  month: string
  calendar?: boolean
}) {
  const query = useInfiniteQuery({
    queryKey: [...recordKeys.all(site), 'feed', filters],
    initialPageParam: 0,
    queryFn: ({ pageParam }) => listRecords(site, filters, pageParam),
    getNextPageParam: (page) => page.next_offset ?? undefined,
  })
  const records = query.data?.pages.flatMap((p) => p.items) ?? []
  return (
    <div className="grid gap-3">
      {query.isPending && (
        <p role="status" className="p-4 text-sm text-[#45564A]">
          Chargement des fiches…
        </p>
      )}
      <ErrorNote error={query.error} />
      {calendar ? (
        <RecordCalendar records={records} month={month} onOpen={onOpen} />
      ) : (
        records.map((record) => (
          <RecordCard
            key={record.id}
            record={record}
            onOpen={onOpen}
            onMove={onMove}
          />
        ))
      )}
      {!query.isPending && !query.isError && !records.length && (
        <p className="rounded-xl border border-dashed border-[#C9D2C7] p-5 text-sm text-[#45564A]">
          Aucune fiche ici.
        </p>
      )}
      {calendar && query.hasNextPage && (
        <p role="status" className="text-sm font-semibold text-[#633900]">
          Vue partielle : d’autres fiches restent à charger.
        </p>
      )}
      {query.hasNextPage && (
        <Button
          variant="outline"
          disabled={query.isFetchingNextPage}
          onClick={() => void query.fetchNextPage()}
        >
          {calendar
            ? 'Afficher davantage de fiches dans le calendrier'
            : 'Afficher la suite'}
        </Button>
      )}
    </div>
  )
}
export function RecordFeedPage({
  establishmentId,
  onNavigate,
  dayOnly = false,
}: {
  establishmentId: string
  onNavigate: (path: string) => void
  dayOnly?: boolean
}) {
  const auth = useAuth()
  const manager = ['owner', 'director', 'manager'].includes(
    auth.memberships.find((m) => m.establishment_id === establishmentId)
      ?.role ?? '',
  )
  const desktop = isDesktopWebLanding(useLgViewport())
  const [mode, setMode] = useState<'list' | 'board' | 'calendar'>('list')
  const [mine, setMine] = useState(dayOnly || !manager)
  const [search, setSearch] = useState('')
  const [pole, setPole] = useState('')
  const options = useQuery({
    queryKey: ['field-record-options', establishmentId],
    queryFn: () => recordOptions(establishmentId),
  })
  const [stage, setStage] = useState<RecordStage | ''>('')
  const [month, setMonth] = useState(new Date().toISOString().slice(0, 7))
  const [closing, setClosing] = useState<FieldRecord | null>(null)
  const [creating, setCreating] = useState(false)
  const [dropError, setDropError] = useState<Error | null>(null)
  const client = useQueryClient()
  const mutation = useMutation({
    mutationFn: ({
      id,
      updated_at,
      stage,
    }: {
      id: string
      updated_at: string
      stage: RecordStage
    }) =>
      updateRecord(establishmentId, id, {
        expected_updated_at: updated_at,
        stage,
      }),
    onSuccess: () =>
      client.invalidateQueries({ queryKey: recordKeys.all(establishmentId) }),
  })
  const open = (id: string) => onNavigate(`/e/${establishmentId}/signals/${id}`)
  const move = (record: FieldRecord, next: RecordStage) =>
    next === 'closed'
      ? setClosing(record)
      : mutation.mutate({
          id: record.id,
          updated_at: record.updated_at,
          stage: next,
        })
  const filters: RecordFilters = {
    mine,
    q: search,
    ...(pole ? { pole } : {}),
    ...(stage ? { stage } : {}),
  }
  const { from, to } = monthWindow(month)
  return (
    <main className="mx-auto h-full overflow-y-auto w-full max-w-[1500px] space-y-5 p-4 pb-24 text-[#17251F] md:p-7">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">
            {dayOnly ? 'Mes fiches' : 'Fiches terrain'}
          </h1>
          <p className="mt-1 text-sm text-[#45564A]">
            Une observation, puis tout son suivi au même endroit.
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={() =>
              void client.invalidateQueries({
                queryKey: recordKeys.all(establishmentId),
              })
            }
            aria-label="Actualiser"
          >
            <RefreshCw size={16} />
          </Button>
          <Button onClick={() => onNavigate(`/e/${establishmentId}/reporting`)}>
            <Plus size={16} /> Une observation
          </Button>
          {manager && (
            <>
              <Button variant="outline" onClick={() => setCreating(true)}>
                Créer une fiche
              </Button>
              <Button
                variant="ghost"
                onClick={() => onNavigate(`/e/${establishmentId}/execution`)}
              >
                Plans et récurrences
              </Button>
            </>
          )}
        </div>
      </header>
      <div className="flex flex-wrap items-center gap-3 rounded-2xl bg-white p-3 shadow-sm">
        <input
          aria-label="Rechercher une fiche"
          placeholder="Rechercher une fiche…"
          className={`${inputClass} max-w-xs`}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select
          aria-label="Filtrer par pôle"
          value={pole}
          onChange={(e) => setPole(e.target.value)}
          className={`${inputClass} max-w-48`}
        >
          <option value="">Tous les pôles</option>
          {options.data?.poles.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={mine}
            onChange={(e) => setMine(e.target.checked)}
          />
          Mes fiches et mes observations
        </label>
        <select
          aria-label="Filtrer par étape"
          className={`${inputClass} max-w-40`}
          value={stage}
          onChange={(e) => setStage(e.target.value as RecordStage | '')}
        >
          <option value="">Toutes les étapes</option>
          {stages.map((s) => (
            <option key={s.id} value={s.id}>
              {s.label}
            </option>
          ))}
        </select>
        <div className="ml-auto flex gap-1" aria-label="Présentation">
          {(
            [
              'list',
              ...(desktop ? (['board'] as const) : []),
              'calendar',
            ] as const
          ).map((view) => (
            <Button
              key={view}
              variant={mode === view ? 'default' : 'outline'}
              onClick={() => setMode(view)}
            >
              {view === 'list'
                ? 'Liste'
                : view === 'board'
                  ? 'Kanban'
                  : 'Calendrier'}
            </Button>
          ))}
        </div>
      </div>
      <ErrorNote error={mutation.error ?? dropError ?? options.error} />
      {mode === 'calendar' && (
        <div className="flex flex-wrap items-center gap-3">
          <label className="text-sm">
            Mois{' '}
            <input
              type="month"
              className="rounded-lg border bg-white p-2 text-[#17251F]"
              value={month}
              onChange={(e) => {
                if (e.target.value) setMonth(e.target.value)
              }}
            />
          </label>
          <span className="text-sm text-[#45564A]">
            De la création à la fin · ◆ échéance · seules les fiches datées
            apparaissent.
          </span>
        </div>
      )}
      {mode === 'board' && desktop ? (
        <div className="grid min-w-[850px] grid-cols-4 gap-4 overflow-x-auto">
          {stages
            .filter((s) => !stage || stage === s.id)
            .map((s) => (
              <section
                key={s.id}
                className="min-h-48 rounded-2xl bg-[#EDF1E9] p-3"
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => {
                  e.preventDefault()
                  try {
                    const drag = JSON.parse(
                      e.dataTransfer.getData('application/spore-record'),
                    ) as { id: string; updated_at: string }
                    if (
                      typeof drag.id !== 'string' ||
                      typeof drag.updated_at !== 'string'
                    )
                      return
                    if (s.id === 'closed') {
                      void getRecord(establishmentId, drag.id)
                        .then(setClosing)
                        .catch((error) =>
                          setDropError(
                            error instanceof Error
                              ? error
                              : new Error('Impossible de charger la fiche.'),
                          ),
                        )
                    } else mutation.mutate({ ...drag, stage: s.id })
                  } catch {
                    /* Ignore unrelated external drops. */
                  }
                }}
              >
                <h2 className="mb-3 flex items-center gap-2 px-1 font-semibold">
                  <ArrowRight size={15} />
                  {s.label}
                </h2>
                <RecordsPane
                  site={establishmentId}
                  filters={{ ...filters, stage: s.id }}
                  onOpen={open}
                  onMove={move}
                  month={month}
                />
              </section>
            ))}
        </div>
      ) : (
        <RecordsPane
          site={establishmentId}
          filters={mode === 'calendar' ? { ...filters, from, to } : filters}
          onOpen={open}
          onMove={move}
          month={month}
          calendar={mode === 'calendar'}
        />
      )}
      {closing && (
        <CloseRecordDialog
          site={establishmentId}
          record={closing}
          onClose={() => setClosing(null)}
        />
      )}
      {creating && (
        <CreateRecord
          site={establishmentId}
          onClose={() => setCreating(false)}
          onCreated={(id) => {
            setCreating(false)
            open(id)
          }}
        />
      )}
    </main>
  )
}
