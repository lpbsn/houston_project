import { useState } from 'react'
import { useInfiniteQuery } from '@tanstack/react-query'
import { AtSign, ChevronDown, ClipboardList, ListFilter, MessageCircle, Search, X } from 'lucide-react'

import { useAppRoute } from '@/app/app-routes'
import { Button } from '@/components/ui/button'
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
    : `/chat/${item.parent_id}?messageId=${item.id}`
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
  const [filtersOpen, setFiltersOpen] = useState(false)
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

  if (tab === 'search') {
    const activeFilterCount = Number(Boolean(author)) + Number(Boolean(date)) + Number(files)
    const filterSummary =
      activeFilterCount === 0
        ? 'Auteur · Depuis · Pièces jointes'
        : `${activeFilterCount} filtre${activeFilterCount > 1 ? 's' : ''} actif${activeFilterCount > 1 ? 's' : ''}`

    return (
      <div className="flex min-h-0 flex-1 flex-col overflow-y-auto bg-[#f7f8f6] text-[#202a26]">
        <div className="mx-auto w-full max-w-[960px] px-4 pt-7 pb-12 max-sm:px-3 max-sm:pt-5 max-sm:pb-9">
          <header className="mb-5 flex items-start justify-between gap-5 max-sm:mb-5 max-sm:gap-2 sm:mb-[23px]">
            <div>
              <h2 className="text-xl leading-tight font-semibold tracking-[-0.6px] sm:text-[23px]">
                Retrouver un échange
              </h2>
              <p className="mt-1.5 text-xs text-[#829087] sm:text-[13px]">
                Messages et commentaires accessibles
              </p>
            </div>
            <button
              type="button"
              aria-label="Fermer la recherche"
              onClick={onCloseSearch}
              className="inline-flex shrink-0 items-center gap-1.5 py-1.5 text-xs font-bold whitespace-nowrap text-[#265d4c] outline-none hover:underline focus-visible:ring-2 focus-visible:ring-[#265d4c]/40"
            >
              <X className="h-[15px] w-[15px]" aria-hidden="true" />
              Fermer
            </button>
          </header>

          <form
            role="search"
            className="flex items-stretch gap-2 sm:gap-[9px]"
            onSubmit={(event) => {
              event.preventDefault()
              setQuery(draft.trim())
            }}
          >
            <label className="flex h-12 min-w-0 flex-1 items-center gap-2.5 rounded-[11px] border border-[#d9e2db] bg-white px-3 shadow-[0_1px_2px_rgba(37,58,46,0.04)] focus-within:border-[#8caf9c] focus-within:shadow-[0_0_0_3px_rgba(38,93,76,0.09)] max-sm:h-[45px] sm:gap-[11px] sm:px-[15px]">
              <Search className="h-[18px] w-[18px] shrink-0 text-[#8c9b91] sm:h-[19px] sm:w-[19px]" aria-hidden="true" />
              <input
                type="search"
                aria-label="Rechercher dans les messages et commentaires"
                placeholder="Rechercher un message, un sujet…"
                value={draft}
                maxLength={150}
                autoComplete="off"
                onChange={(event) => setDraft(event.target.value)}
                className="min-w-0 w-full border-0 bg-transparent text-[13px] text-[#202a26] outline-none placeholder:text-[#9aa49e] sm:text-sm"
              />
            </label>
            <button
              type="submit"
              className="h-12 shrink-0 rounded-[10px] border border-[#265d4c] bg-[#265d4c] px-3 text-xs font-semibold text-white outline-none hover:bg-[#204e40] focus-visible:ring-2 focus-visible:ring-[#265d4c]/40 sm:h-12 sm:min-w-[118px] sm:px-[18px] sm:text-[13px] max-sm:h-[45px]"
            >
              Rechercher
            </button>
          </form>

          <div className="mt-3 mb-5 flex flex-wrap items-center gap-[11px] sm:mb-[25px]">
            <button
              type="button"
              aria-expanded={filtersOpen}
              aria-controls="search-filters"
              onClick={() => setFiltersOpen((open) => !open)}
              className={cn(
                'inline-flex min-h-9 items-center gap-[9px] rounded-lg border border-[#d9e2db] bg-white px-3 py-[9px] text-xs font-semibold text-[#365847] outline-none hover:bg-[#eef4ef] focus-visible:ring-2 focus-visible:ring-[#265d4c]/40',
                filtersOpen && 'bg-[#eef4ef]',
              )}
            >
              <ListFilter className="h-4 w-4 shrink-0" aria-hidden="true" />
              Filtres
              {activeFilterCount > 0 ? (
                <span
                  aria-hidden="true"
                  className="inline-flex h-[18px] min-w-[18px] items-center justify-center rounded-full bg-[#d6e7db] px-1 text-[10px] font-bold text-[#205341]"
                >
                  {activeFilterCount}
                </span>
              ) : null}
              <ChevronDown
                className={cn('h-4 w-4 shrink-0 transition-transform', filtersOpen && 'rotate-180')}
                aria-hidden="true"
              />
            </button>
            <span className="text-[11px] text-[#8b9890] max-[370px]:hidden sm:text-xs">{filterSummary}</span>
          </div>

          <section
            id="search-filters"
            aria-label="Filtres de recherche"
            hidden={!filtersOpen}
            className={cn(
              'mb-5 items-end gap-3 rounded-[11px] border border-[#e1e7e2] bg-white p-[15px] shadow-[0_2px_12px_rgba(34,65,45,0.03)] min-[641px]:-mt-[11px] min-[641px]:mb-[25px]',
              filtersOpen
                ? 'grid grid-cols-1 min-[371px]:grid-cols-2 min-[641px]:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto_auto]'
                : 'hidden',
            )}
          >
            <label className="flex min-w-0 flex-col gap-1.5">
              <span className="text-[11px] font-semibold text-[#6a776d]">Auteur</span>
              <select
                aria-label="Auteur"
                value={author}
                onChange={(event) => setAuthor(event.target.value)}
                className="min-h-[38px] w-full rounded-lg border border-[#d9e2db] bg-white px-2.5 text-xs text-[#3b4b42]"
              >
                <option value="">Tous les auteurs</option>
                {people.data?.items.map((person) => (
                  <option key={person.membership_id} value={person.membership_id}>
                    {person.display_name}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex min-w-0 flex-col gap-1.5">
              <span className="text-[11px] font-semibold text-[#6a776d]">Depuis</span>
              <input
                aria-label="Depuis"
                type="date"
                value={date}
                onChange={(event) => setDate(event.target.value)}
                className="min-h-[38px] w-full rounded-lg border border-[#d9e2db] bg-white px-2.5 text-xs text-[#3b4b42]"
              />
            </label>
            <label className="flex min-h-[38px] items-center gap-1.5 text-xs whitespace-nowrap text-[#48584e] max-[370px]:min-h-[22px]">
              <input
                type="checkbox"
                checked={files}
                onChange={(event) => setFiles(event.target.checked)}
                className="h-[15px] w-[15px] accent-[#265d4c]"
              />
              Avec pièce jointe
            </label>
            <button
              type="button"
              onClick={() => {
                setAuthor('')
                setDate('')
                setFiles(false)
              }}
              className="min-h-[38px] justify-self-start px-1 text-xs font-semibold whitespace-nowrap text-[#265d4c] outline-none hover:underline focus-visible:ring-2 focus-visible:ring-[#265d4c]/40 min-[371px]:justify-self-end min-[641px]:self-center min-[641px]:justify-self-auto max-[370px]:min-h-0"
            >
              Effacer les filtres
            </button>
          </section>

          <div className="mb-[11px] flex items-center justify-between gap-4">
            <h3 className="text-sm leading-snug font-semibold tracking-[-0.1px]">Échanges</h3>
            <p className="hidden text-right text-[11px] text-[#8b9890] min-[641px]:block">
              Ouvrir un résultat pour accéder à sa source
            </p>
          </div>

          {results.isLoading ? <p role="status">Chargement…</p> : null}
          {results.isError ? (
            <div role="alert" className="space-y-2">
              <p>Impossible de charger les échanges.</p>
              <Button variant="outline" onClick={() => void results.refetch()}>
                Réessayer
              </Button>
            </div>
          ) : null}
          {results.isSuccess && items.length === 0 ? (
            <div className="flex min-h-[165px] flex-col items-center justify-center gap-2 rounded-[13px] border border-[#e1e7e2] bg-white px-4 py-6 text-center text-[#7e8e83]">
              <p className="text-[13px] font-semibold text-[#3c5947]">Aucun échange trouvé</p>
              <p className="text-xs">Essayez d&apos;autres mots-clés ou ajustez vos filtres.</p>
            </div>
          ) : null}
          {items.length > 0 ? (
            <ul
              aria-label="Résultats de recherche"
              className="overflow-hidden rounded-[13px] border border-[#e1e7e2] bg-white"
            >
              {items.map((item) => (
                <SearchResultRow
                  key={workspaceItemKey(item)}
                  item={item}
                  onActivate={() => activate(item)}
                />
              ))}
            </ul>
          ) : null}
          {results.hasNextPage ? (
            <div className="flex justify-center pt-4">
              <button
                type="button"
                className="px-3 py-[9px] text-xs font-bold text-[#265d4c] outline-none hover:underline focus-visible:ring-2 focus-visible:ring-[#265d4c]/40 disabled:opacity-50"
                disabled={results.isFetchingNextPage}
                onClick={() => void results.fetchNextPage()}
              >
                Afficher la suite
              </button>
            </div>
          ) : null}
        </div>
      </div>
    )
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
        <ul>
          {items.map((item) => {
            const selectedRow = workspaceItemKey(item) === selectedKey
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
              <PlanDiscussionRow
                key={workspaceItemKey(item)}
                item={item}
                selected={selectedRow}
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
        <WorkspaceSectionHeader
          eyebrow={tab === 'plans' ? 'Échanges contextualisés' : 'Votre activité'}
          title={tab === 'plans' ? 'Commentaires des plans d’action' : 'Mentions'}
          description={
            tab === 'plans'
              ? 'Retrouvez les commentaires associés à vos plans d’action.'
              : 'Retrouvez les messages et commentaires qui vous sollicitent directement.'
          }
        />
      </div>

      {opensDirectly ? (
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
