import { useState } from 'react'
import { useInfiniteQuery } from '@tanstack/react-query'
import { AtSign, ClipboardList, MessageCircle, Search, X } from 'lucide-react'

import { useAppRoute } from '@/app/app-routes'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'

import { useEligibleChatMembershipsQuery } from '../hooks'
import { fetchWorkspace, type WorkspaceFilter, type WorkspaceItem } from '../workspace-api'
import {
  MentionRow,
  PlanDiscussionRow,
  SearchResultRow,
  WorkspaceFilterChips,
  WorkspacePreview,
  WorkspaceSectionHeader,
  workspaceItemKey,
} from './workspace-presentation'

export type CommunicationTab = 'team' | 'plans' | 'mentions'
export type WorkspaceView = 'plans' | 'mentions' | 'search'
export type WorkspaceMode = 'pane' | 'direct'

const TABS = [
  ['team', 'Discussions', MessageCircle],
  ['plans', 'Plans d’action', ClipboardList],
  ['mentions', 'Mentions', AtSign],
] as const

export function CommunicationTabs({
  tab,
  onChange,
  searchOpen,
  onSearch,
  compactSearch,
}: {
  tab: CommunicationTab
  onChange: (tab: CommunicationTab) => void
  searchOpen: boolean
  onSearch: () => void
  compactSearch: boolean
}) {
  return (
    <nav
      aria-label="Espaces de discussion"
      className="flex shrink-0 items-stretch justify-between gap-3 border-b border-[#E8E6DF] bg-white px-3"
    >
      <div className="flex min-w-0 gap-1 overflow-x-auto">
        {TABS.map(([key, label, Icon]) => {
          const active = tab === key
          return (
            <button
              key={key}
              type="button"
              aria-current={active ? 'page' : undefined}
              onClick={() => onChange(key)}
              className={cn(
                '-mb-px inline-flex shrink-0 items-center gap-1.5 border-b-2 bg-transparent px-2 py-3 text-sm font-semibold outline-none focus-visible:ring-2 focus-visible:ring-[#265d4c]/40',
                active
                  ? 'border-[#236c55] text-[#1d5949]'
                  : 'border-transparent text-[#6d7c72]',
              )}
            >
              <Icon className="h-4 w-4" aria-hidden="true" />
              {label}
            </button>
          )
        })}
      </div>
      <button
        type="button"
        aria-label="Rechercher dans les échanges"
        aria-pressed={searchOpen}
        onClick={onSearch}
        className={cn(
          'my-2 inline-flex shrink-0 items-center justify-center self-center rounded-lg text-[#5c6b62] outline-none hover:bg-[#f4f7f3] hover:text-[#1d5949] focus-visible:ring-2 focus-visible:ring-[#265d4c]/40',
          compactSearch ? 'h-9 w-9' : 'h-9 gap-2 px-2.5 text-sm',
          searchOpen && 'bg-[#e7f2ec] text-[#1d5949]',
        )}
      >
        <Search className="h-4 w-4" aria-hidden="true" />
        {compactSearch ? null : <span>Rechercher dans les échanges</span>}
      </button>
    </nav>
  )
}

export function workspaceHref(establishmentId: string, item: WorkspaceItem) {
  return item.kind === 'plan'
    ? `/e/${establishmentId}/execution/${item.parent_id}?tab=comments&commentId=${item.id}`
    : `/e/${establishmentId}/chat/${item.parent_id}?messageId=${item.id}`
}

function emptyCopy(tab: WorkspaceView, unresolved: boolean): string {
  if (tab === 'plans') {
    return unresolved ? 'Aucune discussion non résolue.' : 'Aucune discussion de plan.'
  }
  if (tab === 'mentions') {
    return 'Aucune mention pour le moment'
  }
  return 'Aucun échange à afficher.'
}

export function CommunicationWorkspace({
  establishmentId,
  tab,
  mode,
  onOpenItem,
  onCloseSearch,
}: {
  onOpenItem: () => void
  onCloseSearch?: () => void
  establishmentId: string
  tab: WorkspaceView
  mode: WorkspaceMode
}) {
  const { navigate } = useAppRoute()
  const [draft, setDraft] = useState('')
  const [query, setQuery] = useState('')
  const [unresolvedOnly, setUnresolvedOnly] = useState(false)
  const [author, setAuthor] = useState('')
  const [date, setDate] = useState('')
  const [files, setFiles] = useState(false)
  const [selectedKey, setSelectedKey] = useState<string | null>(null)
  const [selectionScope, setSelectionScope] = useState('')
  const people = useEligibleChatMembershipsQuery(establishmentId, '', { enabled: tab === 'search' })
  const opensDirectly = tab === 'search' || mode === 'direct'
  const filters: WorkspaceFilter = {
    tab,
    q: query,
    unresolved: tab === 'plans' && unresolvedOnly,
    ...(author ? { author_id: author } : {}),
    ...(date ? { after: new Date(`${date}T00:00:00`).toISOString() } : {}),
    files_only: files,
  }
  const results = useInfiniteQuery({
    queryKey: ['chat', 'workspace', establishmentId, filters],
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam }) => fetchWorkspace(establishmentId, { ...filters, cursor: pageParam }),
    getNextPageParam: (page) => page.cursor ?? undefined,
    refetchInterval: 30000,
  })
  const items = results.data?.pages.flatMap((page) => page.items) ?? []
  const visibleKeys = items.map(workspaceItemKey).join('\n')
  if (selectionScope !== visibleKeys) {
    setSelectionScope(visibleKeys)
    if (selectedKey && !visibleKeys.split('\n').filter(Boolean).includes(selectedKey)) {
      setSelectedKey(null)
    }
  }
  const selected = items.find((item) => workspaceItemKey(item) === selectedKey) ?? null

  function openItem(item: WorkspaceItem) {
    onOpenItem()
    navigate(workspaceHref(establishmentId, item))
  }

  function activate(item: WorkspaceItem) {
    if (opensDirectly) {
      openItem(item)
      return
    }
    setSelectedKey(workspaceItemKey(item))
  }

  const mentionsEmpty = tab === 'mentions' && results.isSuccess && items.length === 0
  const list = (
    <div className={mentionsEmpty ? 'flex w-full justify-center' : undefined}>
      {results.isLoading ? <p role="status">Chargement…</p> : null}
      {results.isError ? (
        <div role="alert" className="space-y-2">
          <p>Impossible de charger les échanges.</p>
          <Button variant="outline" onClick={() => void results.refetch()}>
            Réessayer
          </Button>
        </div>
      ) : null}
      {mentionsEmpty ? (
        <p className="text-center text-sm italic text-[#8aa094]">{emptyCopy(tab, unresolvedOnly)}</p>
      ) : null}
      {results.isSuccess && items.length === 0 && !mentionsEmpty ? (
        <p>{emptyCopy(tab, unresolvedOnly)}</p>
      ) : null}
      {items.length > 0 ? (
        <ul className={tab === 'search' ? 'space-y-2' : undefined}>
          {items.map((item) => {
            const selectedRow = workspaceItemKey(item) === selectedKey
            if (tab === 'plans') {
              return (
                <PlanDiscussionRow
                  key={workspaceItemKey(item)}
                  item={item}
                  selected={selectedRow}
                  onActivate={() => activate(item)}
                />
              )
            }
            if (tab === 'mentions') {
              return (
                <MentionRow
                  key={workspaceItemKey(item)}
                  item={item}
                  selected={selectedRow}
                  onActivate={() => activate(item)}
                />
              )
            }
            return (
              <SearchResultRow
                key={workspaceItemKey(item)}
                item={item}
                onActivate={() => activate(item)}
              />
            )
          })}
        </ul>
      ) : null}
      {results.hasNextPage ? (
        <Button
          variant="outline"
          className="mt-3"
          disabled={results.isFetchingNextPage}
          onClick={() => void results.fetchNextPage()}
        >
          Afficher la suite
        </Button>
      ) : null}
    </div>
  )

  const panel = (
    <section
      className={cn(
        'flex min-h-0 flex-col overflow-hidden rounded-2xl border border-[#e1e9e0] bg-white',
        mentionsEmpty && 'min-h-full flex-1',
      )}
    >
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#eef2ee] px-4 py-3">
        <h3 className="text-sm font-semibold text-[#1a1a1a]">
          {tab === 'plans' ? 'Plans avec commentaires' : 'Dernières mentions'}
        </h3>
        {tab === 'plans' ? (
          <WorkspaceFilterChips unresolved={unresolvedOnly} onChange={setUnresolvedOnly} />
        ) : (
          <p className="text-[11px] text-[#8aa094]">Les plus récentes d’abord</p>
        )}
      </div>
      <div
        className={cn(
          'min-h-0',
          mentionsEmpty && 'flex flex-1 items-center justify-center',
          !opensDirectly && 'overflow-y-auto',
          !opensDirectly || mentionsEmpty ? 'flex-1' : undefined,
        )}
      >
        {list}
      </div>
      <p className="border-t border-[#eef2ee] px-4 py-2 text-[11px] text-[#8aa094]">
        {tab === 'mentions'
          ? 'L’accès aux échanges respecte votre périmètre d’établissement.'
          : 'Affichage des échanges accessibles selon vos permissions.'}
      </p>
    </section>
  )

  return (
    <div className="flex min-h-0 flex-1 flex-col bg-[#f7f8f6] text-[#1a1a1a]">
      <div className="shrink-0 px-4 pt-4 pb-3">
        {tab === 'search' ? (
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="text-xl font-semibold tracking-tight">Retrouver une information</h2>
              <p className="mt-1 text-[13px] text-[#6d7c72]">
                Recherche dans les messages et les commentaires accessibles.
              </p>
            </div>
            <button
              type="button"
              onClick={onCloseSearch}
              className="inline-flex h-9 items-center gap-1 rounded-lg px-2 text-sm font-semibold text-[#1d5949] outline-none hover:bg-[#e7f2ec] focus-visible:ring-2 focus-visible:ring-[#265d4c]/40"
            >
              <X className="h-4 w-4" aria-hidden="true" />
              Fermer
            </button>
          </div>
        ) : (
          <WorkspaceSectionHeader
            eyebrow={tab === 'plans' ? 'Échanges contextualisés' : 'Votre activité'}
            title={tab === 'plans' ? 'Commentaires des plans d’action' : 'Mentions'}
            description={
              tab === 'plans'
                ? 'Retrouvez les commentaires associés à vos plans d’action.'
                : 'Retrouvez les messages et commentaires qui vous sollicitent directement.'
            }
          />
        )}
      </div>

      {tab === 'search' ? (
        <form
          className="shrink-0 space-y-3 px-4 pb-3"
          onSubmit={(event) => {
            event.preventDefault()
            setQuery(draft.trim())
          }}
        >
          <div className="flex gap-2">
            <Input
              aria-label="Rechercher dans les messages"
              placeholder="Devis, livraison, affiches…"
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              maxLength={150}
            />
            <Button type="submit">Rechercher</Button>
          </div>
          <div className="flex flex-wrap items-center gap-3 text-sm">
            <label>
              Auteur{' '}
              <select
                aria-label="Auteur"
                value={author}
                onChange={(event) => setAuthor(event.target.value)}
                className="rounded-lg border border-[#E8E6DF] bg-white p-2"
              >
                <option value="">Tous</option>
                {people.data?.items.map((person) => (
                  <option key={person.membership_id} value={person.membership_id}>
                    {person.display_name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Depuis{' '}
              <input
                aria-label="Depuis"
                type="date"
                value={date}
                onChange={(event) => setDate(event.target.value)}
                className="rounded-lg border border-[#E8E6DF] bg-white p-2"
              />
            </label>
            <label>
              <input
                type="checkbox"
                checked={files}
                onChange={(event) => setFiles(event.target.checked)}
              />{' '}
              Avec pièce jointe
            </label>
          </div>
        </form>
      ) : null}

      {tab === 'search' ? (
        <div className="min-h-0 flex-1 overflow-y-auto px-4 pb-4">{list}</div>
      ) : opensDirectly ? (
        <div
          className={cn(
            'min-h-0 flex-1 overflow-y-auto px-4 pb-4',
            mentionsEmpty && 'flex flex-col',
          )}
        >
          {panel}
        </div>
      ) : (
        <div className="grid min-h-0 flex-1 grid-cols-[minmax(0,1.55fr)_minmax(17rem,1fr)] gap-4 px-4 pb-4">
          {panel}
          <WorkspacePreview item={selected} onOpen={openItem} />
        </div>
      )}
    </div>
  )
}
