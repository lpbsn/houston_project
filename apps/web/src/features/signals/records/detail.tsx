import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query'
import { useState } from 'react'
import { ArrowLeft, Bell, CalendarDays, Plus, UserRound } from 'lucide-react'
import { useSignalDetailQuery } from '../hooks'
import { SignalDetailPhotoSection } from '../components/signal-detail-photo-section'
import { OriginalObservation } from '../components/original-observation'
import { SignalQualifyRoutingSheet } from '../components/signal-qualify-routing-sheet'
import { useSignalQualifySheet } from '../hooks/use-signal-qualify-sheet'
import { parseDetailDeepLink } from '@/features/comments/lib/detail-deep-link'
import { useLocationSearch } from '@/lib/location-search'
import { Button } from '@/components/ui/button'
import { CommentSection } from '@/features/comments/components/comment-section'
import {
  commandRecord,
  getRecord,
  recordKeys,
  recordSection,
  type FieldRecord,
  type RecordStage,
} from './api'
import {
  CloseRecordDialog,
  dateLabel,
  ErrorNote,
  inputClass,
  panelClass,
  stages,
  useRecordUpdate,
} from './shared'
import { RecordWorkPanel } from './work-panel'
import { RecordForm } from './forms'
import { RecordPinning } from './pinning'
import { OrganizationDialog, ProjectContents } from './organization'
import { PlanningDialog, type PlanningDraft } from './planning-dialog'
import { RecordDocuments } from './documents'
import { CreateRecord } from './feed'

function RecordSection({
  site,
  record,
  section,
  onNavigate,
}: {
  site: string
  record: FieldRecord
  section: 'sources' | 'work' | 'history' | 'objectives'
  onNavigate: (path: string) => void
}) {
  const [expanded, setExpanded] = useState<string | null>(null)
  const query = useInfiniteQuery({
    queryKey: [...recordKeys.detail(site, record.id), section],
    initialPageParam: 0,
    queryFn: ({ pageParam }) =>
      recordSection(site, record.id, section, pageParam),
    getNextPageParam: (page) => page.next_offset ?? undefined,
  })
  const items = query.data?.pages.flatMap((p) => p.items) ?? []
  return (
    <div className="space-y-3">
      <ErrorNote error={query.error} />
      {query.isPending && (
        <p role="status" className="text-sm">
          Chargement…
        </p>
      )}
      {items.map((item) => (
        <div key={item.id} className="rounded-xl border border-[#DADFD8] p-4">
          {section === 'work' ? (
            <>
              <button
                className="flex w-full items-center justify-between gap-2 text-left font-semibold"
                aria-expanded={expanded === item.id}
                onClick={() =>
                  setExpanded(expanded === item.id ? null : item.id)
                }
              >
                {item.title}
                <Plus size={16} />
              </button>
              {expanded === item.id && (
                <div className="mt-4">
                  <RecordWorkPanel
                    site={site}
                    executionId={item.id}
                    record={record}
                    onNavigate={onNavigate}
                  />
                </div>
              )}
            </>
          ) : (
            <>
              <p className="font-semibold">{item.title}</p>
              {item.author && (
                <p className="mt-1 text-xs text-[#45564A]">
                  {item.author} ·{' '}
                  {item.date && new Date(item.date).toLocaleString('fr-FR')}
                </p>
              )}
              {item.text && (
                <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed">
                  {item.text}
                </p>
              )}
              {section === 'objectives' && (
                <p className="mt-2 text-sm font-medium">
                  {(
                    {
                      accepted: 'Objectif validé',
                      modified: 'Objectif modifié et validé',
                      refused: 'Objectif refusé',
                      recorded: 'À valider',
                    } as Record<string, string>
                  )[item.status] ?? item.status}{' '}
                  · Le résultat sera vérifié dans Brain.
                </p>
              )}
            </>
          )}
        </div>
      ))}
      {!items.length && !query.isPending && !query.isError && (
        <p className="text-sm text-[#45564A]">
          {section === 'work'
            ? 'Aucune tâche obligatoire. Ajoutez du travail si le sujet le nécessite.'
            : section === 'objectives'
              ? 'Aucun objectif KPI rattaché pour le moment.'
              : 'Aucun élément pour le moment.'}
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
export function RecordDetailPage({
  establishmentId: site,
  recordId,
  onNavigate,
  onBack,
}: {
  establishmentId: string
  recordId: string
  onNavigate: (path: string) => void
  onBack?: () => void
}) {
  const query = useQuery({
    queryKey: recordKeys.detail(site, recordId),
    queryFn: () => getRecord(site, recordId),
  })
  const client = useQueryClient()
  const original = useSignalDetailQuery(site, recordId)
  const deepLink = parseDetailDeepLink(useLocationSearch())
  const qualification = useSignalQualifySheet({
    establishmentId: site,
    onNavigate: (path) => onNavigate(`/e/${site}${path}`),
  })
  const update = useRecordUpdate(site, recordId)
  const [closing, setClosing] = useState(false)
  const [organizing, setOrganizing] = useState<'project' | 'dependency' | null>(
    null,
  )
  const [planning, setPlanning] = useState<PlanningDraft | null>(null)
  const [creating, setCreating] = useState(false)
  const [form, setForm] = useState<
    'details' | 'work' | 'participants' | 'objective' | 'link' | null
  >(null)
  const [tab, setTab] = useState<
    | 'work'
    | 'sources'
    | 'chat'
    | 'history'
    | 'objectives'
    | 'documents'
    | 'children'
    | null
  >(() => (deepLink.tab ? 'chat' : null))
  const follow = useMutation({
    mutationFn: (enabled: boolean) =>
      commandRecord(site, recordId, {
        command: 'follow',
        enabled,
        expected_updated_at: query.data!.updated_at,
      }),
  })
  const record = query.data
  if (!record)
    return (
      <div className="p-6">
        <ErrorNote error={query.error} />
        {query.isPending && <p role="status">Chargement de la fiche…</p>}
        <Button
          variant="outline"
          onClick={() => onNavigate(`/e/${site}/signals`)}
        >
          Retour aux fiches
        </Button>
      </div>
    )
  const activeTab = tab ?? (record.is_project ? 'children' : 'work')
  return (
    <main className="mx-auto h-full w-full overflow-y-auto max-w-6xl space-y-5 p-4 pb-24 text-[#17251F] md:p-7">
      <button
        className="flex items-center gap-2 text-sm font-medium"
        onClick={onBack ?? (() => onNavigate(`/e/${site}/signals`))}
      >
        <ArrowLeft size={16} />
        Toutes les fiches
      </button>
      {record.parent_project && (
        <button
          className="text-sm font-semibold text-[#075940] hover:underline"
          onClick={() =>
            onNavigate(`/e/${site}/signals/${record.parent_project!.id}`)
          }
        >
          Projet · {record.parent_project.name}
        </button>
      )}
      <header className={`${panelClass} space-y-4`}>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="mb-2 text-sm font-semibold text-[#075940]">
              {record.pole}
              {record.is_project
                ? ' · Projet'
                : record.is_milestone
                  ? ' · Jalon'
                  : ''}
            </p>
            <h1 className="max-w-3xl text-2xl font-semibold leading-snug">
              {record.title}
            </h1>
          </div>
          {record.can_progress && (
            <select
              aria-label="Étape de la fiche"
              className={`${inputClass} max-w-44`}
              value={record.stage}
              disabled={update.isPending}
              onChange={(e) => {
                const stage = e.target.value as RecordStage
                if (stage === 'closed') setClosing(true)
                else
                  update.mutate({
                    expected_updated_at: record.updated_at,
                    stage,
                  })
              }}
            >
              {stages
                .filter(
                  (s) =>
                    record.can_manage ||
                    ['doing', 'review', record.stage].includes(s.id),
                )
                .map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.label}
                  </option>
                ))}
            </select>
          )}
        </div>
        {record.summary && (
          <p className="max-w-4xl whitespace-pre-wrap text-sm leading-relaxed">
            {record.summary}
          </p>
        )}
        <div className="flex flex-wrap gap-4 text-sm">
          <span className="flex items-center gap-2">
            <UserRound size={16} />
            {record.owner?.name ?? 'Responsable à définir'}
          </span>
          <span className="flex items-center gap-2">
            <CalendarDays size={16} />
            {record.planned_start_on
              ? `${dateLabel(record.planned_start_on)} → `
              : ''}
            {record.due_on ? dateLabel(record.due_on) : 'Sans échéance'}
          </span>
          <span>
            {record.observation_count} observation
            {record.observation_count > 1 ? 's' : ''} conservée
            {record.observation_count > 1 ? 's' : ''}
          </span>
        </div>
        {record.stage === 'review' && (
          <p className="rounded-xl bg-[#E6F0FF] p-3 text-sm text-[#143D6B]">
            Le travail est terminé. Vérifiez sur le terrain si le problème est
            réellement résolu.
          </p>
        )}
        {record.stage === 'closed' && (
          <p className="rounded-xl bg-[#E5F1E7] p-3 text-sm text-[#164C27]">
            {record.closure_reason === 'resolved'
              ? 'Résolution confirmée.'
              : record.closure_reason === 'acknowledged'
                ? 'Information prise en compte.'
                : 'Fiche close.'}{' '}
            L’historique est conservé. Un objectif KPI reste à vérifier
            indépendamment.
          </p>
        )}
        {record.blocked_reason && (
          <p className="rounded-xl bg-[#FFF0CF] p-3 text-sm text-[#633900]">
            Bloqué · {record.blocked_reason}
            {record.waiting_for
              ? ` · En attente de ${record.waiting_for.name}`
              : ''}
          </p>
        )}
        {record.planning_predecessor && (
          <p className="text-sm text-[#45564A]">
            À planifier après{' '}
            <button
              className="font-semibold text-[#075940] underline"
              onClick={() =>
                onNavigate(
                  `/e/${site}/signals/${record.planning_predecessor!.id}`,
                )
              }
            >
              {record.planning_predecessor.name}
            </button>
          </p>
        )}
        <div className="flex flex-wrap items-center gap-2">
          {record.can_manage && record.stage !== 'closed' && (
            <>
              <Button
                onClick={() =>
                  record.is_project ? setCreating(true) : setForm('work')
                }
              >
                <Plus size={15} />
                {record.is_project ? 'Ajouter une fiche' : 'Ajouter du travail'}
              </Button>
              <Button
                variant="outline"
                onClick={() =>
                  setPlanning({
                    record,
                    start:
                      record.planned_start_on ?? record.calendar?.start ?? '',
                    due: record.due_on ?? '',
                  })
                }
              >
                <CalendarDays size={15} />
                Planifier
              </Button>
            </>
          )}
          <Button
            variant="outline"
            disabled={follow.isPending}
            onClick={() => follow.mutate(true)}
          >
            <Bell size={15} />
            Suivre
          </Button>
          <details className="relative">
            <summary className="cursor-pointer list-none rounded-xl border border-[#C9D2C7] bg-white px-4 py-2 text-sm font-semibold hover:bg-[#F2F7F0] focus-visible:outline-2 focus-visible:outline-[#075940]">
              Plus d’options
            </summary>
            <div
              className="absolute left-0 top-full z-30 mt-2 grid min-w-64 gap-1 rounded-xl border border-[#C9D2C7] bg-white p-2 shadow-lg"
              onClick={(e) => {
                const details = e.currentTarget.closest('details')
                if (details) details.open = false
              }}
            >
              {record.can_manage && (
                <>
                  <Button
                    variant="ghost"
                    className="justify-start"
                    onClick={() => setForm('details')}
                  >
                    Responsable et blocage
                  </Button>
                  <Button
                    variant="ghost"
                    className="justify-start"
                    onClick={() => setForm('participants')}
                  >
                    Participants
                  </Button>
                  <Button
                    variant="ghost"
                    className="justify-start"
                    onClick={() => setOrganizing('project')}
                  >
                    Organiser dans un projet
                  </Button>
                  {record.stage !== 'closed' && (
                    <>
                      <Button
                        variant="ghost"
                        className="justify-start"
                        onClick={() => setOrganizing('dependency')}
                      >
                        Définir un préalable
                      </Button>
                      <Button
                        variant="ghost"
                        className="justify-start"
                        onClick={() => setForm('link')}
                      >
                        Rattacher un plan
                      </Button>
                      {record.is_project && (
                        <Button
                          variant="ghost"
                          className="justify-start"
                          onClick={() => setForm('work')}
                        >
                          Ajouter du travail au projet
                        </Button>
                      )}
                    </>
                  )}
                  {original.data?.permission_hints.can_qualify_routing && (
                    <Button
                      variant="ghost"
                      className="justify-start"
                      onClick={() =>
                        void qualification.openForSignal(record.id)
                      }
                    >
                      Pôle et sujet
                    </Button>
                  )}
                </>
              )}
              {original.data && (
                <RecordPinning site={site} signal={original.data} />
              )}
              <Button
                variant="ghost"
                className="justify-start"
                disabled={follow.isPending}
                onClick={() => follow.mutate(false)}
              >
                Couper les alertes
              </Button>
            </div>
          </details>
        </div>
        {follow.isSuccess && (
          <p role="status" className="text-sm text-[#075940]">
            Préférence de suivi enregistrée.
          </p>
        )}
        <ErrorNote error={update.error ?? follow.error} />
      </header>
      <section className={panelClass}>
        <nav
          className="mb-5 flex gap-2 overflow-x-auto border-b border-[#DADFD8] pb-3"
          aria-label="Contenu de la fiche"
        >
          {(
            [
              ...(record.is_project
                ? [{ id: 'children' as const, label: 'Fiches du projet' }]
                : []),
              { id: 'work', label: 'Travail' },
              { id: 'documents', label: 'Documents' },
              { id: 'sources', label: 'Observations' },
              { id: 'chat', label: 'Discussion' },
              { id: 'history', label: 'Historique' },
              { id: 'objectives', label: 'Impact KPI' },
            ] as const
          )
            .filter((t) => t.id !== 'objectives' || record.can_use_brain)
            .map((t) => (
              <Button
                key={t.id}
                variant={activeTab === t.id ? 'default' : 'outline'}
                aria-pressed={activeTab === t.id}
                onClick={() => setTab(t.id)}
              >
                {t.label}
              </Button>
            ))}
        </nav>
        {activeTab === 'sources' && original.data && (
          <div className="mb-4 space-y-3">
            <SignalDetailPhotoSection mediaItems={original.data.media_items} />
            <OriginalObservation signal={original.data} />
          </div>
        )}
        {activeTab === 'objectives' && record.can_use_brain && (
          <Button
            variant="outline"
            className="mb-4"
            onClick={() => setForm('objective')}
          >
            Rattacher un objectif Brain
          </Button>
        )}
        {activeTab === 'children' ? (
          <ProjectContents
            site={site}
            record={record}
            onOpen={(id) => onNavigate(`/e/${site}/signals/${id}`)}
            onCreate={() => setCreating(true)}
          />
        ) : activeTab === 'documents' ? (
          <>
            <RecordDocuments
              site={site}
              record={record}
              onNavigate={onNavigate}
              onWork={() => setTab('work')}
            />
            {original.data && original.data.media_items.length > 0 && (
              <div className="mt-6 border-t border-[#DADFD8] pt-5">
                <h3 className="mb-3 font-semibold">Photos des observations</h3>
                <SignalDetailPhotoSection
                  mediaItems={original.data.media_items}
                />
              </div>
            )}
          </>
        ) : activeTab === 'chat' ? (
          <CommentSection
            establishmentId={site}
            targetType="signal"
            targetId={record.id}
            highlightCommentId={deepLink.commentId}
            documentFlow
            pinComposer={false}
          />
        ) : (
          <RecordSection
            key={activeTab}
            site={site}
            record={record}
            section={activeTab}
            onNavigate={onNavigate}
          />
        )}
      </section>
      {qualification.open && qualification.signal && (
        <SignalQualifyRoutingSheet
          open
          establishmentId={site}
          signal={qualification.signal}
          isPending={qualification.isPending}
          errorMessage={qualification.errorMessage}
          onClose={qualification.close}
          onSubmit={async (body) => {
            await qualification.submit(body)
            await client.invalidateQueries({ queryKey: recordKeys.all(site) })
          }}
        />
      )}
      {organizing && (
        <OrganizationDialog
          site={site}
          record={record}
          dependency={organizing === 'dependency'}
          onClose={() => setOrganizing(null)}
        />
      )}
      {planning && (
        <PlanningDialog
          site={site}
          draft={planning}
          onClose={() => setPlanning(null)}
        />
      )}
      {creating && (
        <CreateRecord
          site={site}
          parentProject={record}
          onClose={() => setCreating(false)}
          onCreated={(id) => {
            setCreating(false)
            void client.invalidateQueries({ queryKey: recordKeys.all(site) })
            onNavigate(`/e/${site}/signals/${id}`)
          }}
        />
      )}
      {form && (
        <RecordForm
          site={site}
          record={record}
          kind={form}
          onClose={() => setForm(null)}
        />
      )}
      {closing && (
        <CloseRecordDialog
          site={site}
          record={record}
          onClose={() => setClosing(false)}
        />
      )}
    </main>
  )
}
