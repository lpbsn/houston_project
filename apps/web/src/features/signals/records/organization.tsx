import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query'
import { useState } from 'react'
import { FolderKanban, Milestone } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { TerrainDialog } from '@/components/ui/terrain/terrain-dialog'
import {
  listRecords,
  organizeRecord,
  recordKeys,
  recordOptions,
  setPredecessor,
  type FieldRecord,
} from './api'
import { dateLabel, ErrorNote, inputClass, stages } from './shared'

export function OrganizationDialog({
  site,
  record,
  dependency = false,
  onClose,
}: {
  site: string
  record: FieldRecord
  dependency?: boolean
  onClose: () => void
}) {
  const [search, setSearch] = useState('')
  const [parent, setParent] = useState(record.parent_project?.id ?? '')
  const [previous, setPrevious] = useState(
    record.planning_predecessor?.id ?? '',
  )
  const [kind, setKind] = useState(
    record.is_project
      ? 'project'
      : record.is_milestone
        ? 'milestone'
        : 'record',
  )
  const query = useQuery({
    queryKey: ['field-record-options', site, search],
    queryFn: () => recordOptions(site, search),
  })
  const client = useQueryClient()
  const mutation = useMutation({
    mutationFn: () =>
      dependency
        ? setPredecessor(site, record.id, {
            expected_updated_at: record.updated_at,
            predecessor_id: previous || null,
          })
        : organizeRecord(site, record.id, {
            expected_updated_at: record.updated_at,
            parent_project_id: parent || null,
            is_project: kind === 'project',
            is_milestone: kind === 'milestone',
          }),
    onSuccess: async () => {
      await client.invalidateQueries({ queryKey: recordKeys.all(site) })
      void client.invalidateQueries({
        queryKey: ['field-record-options', site],
      })
      onClose()
    },
  })
  const choices = dependency ? query.data?.records : query.data?.projects
  const current = dependency
    ? record.planning_predecessor
    : record.parent_project
  const options = [
    ...(current ? [current] : []),
    ...(choices ?? []).filter(
      (item) => item.id !== record.id && item.id !== current?.id,
    ),
  ]
  return (
    <TerrainDialog
      open
      title={
        dependency ? 'Préalable de planification' : 'Organiser dans un projet'
      }
      onClose={onClose}
      dismissible={!mutation.isPending}
    >
      <form
        className="grid gap-4 text-[#17251F]"
        onSubmit={(e) => {
          e.preventDefault()
          mutation.mutate()
        }}
      >
        {!dependency && (
          <label className="grid gap-2 text-sm">
            Format
            <select
              className={inputClass}
              value={kind}
              onChange={(e) => setKind(e.target.value)}
            >
              <option value="record">Fiche</option>
              {record.kind === 'project' && (
                <option value="project">
                  Projet regroupant plusieurs fiches
                </option>
              )}
              <option value="milestone">Jalon · une date clé</option>
            </select>
          </label>
        )}
        <label className="grid gap-2 text-sm">
          Rechercher par titre
          <input
            className={inputClass}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </label>
        <label className="grid gap-2 text-sm">
          {dependency ? 'Commence après cette fiche' : 'Projet parent'}
          <select
            className={inputClass}
            value={dependency ? previous : parent}
            onChange={(e) =>
              dependency
                ? setPrevious(e.target.value)
                : setParent(e.target.value)
            }
          >
            <option value="">Aucun</option>
            {options.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </label>
        <p className="text-sm leading-relaxed text-[#45564A]">
          {dependency
            ? 'La fiche commence au plus tôt le lendemain de l’échéance de son préalable. Planifiez ses dates avant de créer ce lien. Cela ne valide ni les tâches ni la résolution.'
            : 'Les fiches conservent leurs responsables, leurs discussions et leurs droits. Trois niveaux maximum : projet, sous-projet, fiche.'}
        </p>
        <ErrorNote error={mutation.error ?? query.error} />
        <Button disabled={mutation.isPending || query.isPending} type="submit">
          Enregistrer
        </Button>
      </form>
    </TerrainDialog>
  )
}

export function ProjectContents({
  site,
  record,
  onOpen,
  onCreate,
}: {
  site: string
  record: FieldRecord
  onOpen: (id: string) => void
  onCreate: () => void
}) {
  const query = useInfiniteQuery({
    queryKey: [...recordKeys.detail(site, record.id), 'children'],
    initialPageParam: 0,
    queryFn: ({ pageParam }) =>
      listRecords(site, { project: record.id }, pageParam),
    getNextPageParam: (page) => page.next_offset ?? undefined,
  })
  const rows = query.data?.pages.flatMap((page) => page.items) ?? []
  const count = record.visible_child_count
  const done = record.visible_closed_child_count
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="font-semibold">Fiches de ce projet</h2>
          <p className="mt-1 text-sm text-[#45564A]">
            {done} / {count} fiches accessibles closes · la clôture ne mesure
            pas le résultat KPI.
          </p>
        </div>
        {record.can_manage && (
          <Button variant="outline" onClick={onCreate}>
            Ajouter une fiche
          </Button>
        )}
      </div>
      <div
        role="progressbar"
        aria-label="Fiches accessibles closes"
        aria-valuemin={0}
        aria-valuemax={count || 1}
        aria-valuenow={done}
        className="h-2 overflow-hidden rounded-full bg-[#E5EBE3]"
      >
        <div
          className="h-full bg-[#075940]"
          style={{ width: `${count ? (done / count) * 100 : 0}%` }}
        />
      </div>
      <ErrorNote error={query.error} />
      {query.isPending && <p role="status">Chargement…</p>}
      {rows.map((row) => (
        <button
          key={row.id}
          onClick={() => onOpen(row.id)}
          className="flex w-full items-center gap-3 rounded-xl border border-[#DADFD8] bg-white p-4 text-left text-[#17251F] hover:bg-[#F2F7F0] focus-visible:outline-2 focus-visible:outline-[#075940]"
        >
          {row.is_milestone ? (
            <Milestone size={18} />
          ) : (
            <FolderKanban size={18} />
          )}
          <span className="min-w-0 flex-1">
            <strong className="block truncate text-sm">{row.title}</strong>
            <span className="mt-1 block text-xs text-[#45564A]">
              {row.pole} · {row.owner?.name ?? 'À attribuer'}
              {row.due_on ? ` · ${dateLabel(row.due_on)}` : ''}
            </span>
          </span>
          <span className="rounded-lg bg-[#EEF3EA] px-2 py-1 text-xs font-medium">
            {stages.find((s) => s.id === row.stage)?.label}
          </span>
        </button>
      ))}
      {!rows.length && !query.isPending && !query.isError && (
        <p className="rounded-xl border border-dashed border-[#BCCDBD] p-5 text-sm text-[#45564A]">
          Aucune fiche accessible dans ce projet. Ajoutez-en une ou rattachez
          une fiche existante depuis son menu Organiser.
        </p>
      )}
      {query.hasNextPage && (
        <Button
          variant="outline"
          disabled={query.isFetchingNextPage}
          onClick={() => void query.fetchNextPage()}
        >
          Afficher la suite
        </Button>
      )}
    </div>
  )
}
