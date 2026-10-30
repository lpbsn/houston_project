import { useState } from 'react'
import { useInfiniteQuery } from '@tanstack/react-query'
import { useAppRoute } from '@/app/app-routes'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { fetchWorkspace, type WorkspaceFilter, type WorkspaceItem } from '../workspace-api'
import { useEligibleChatMembershipsQuery } from '../hooks'

export type CommunicationTab = 'team' | 'plans' | 'mentions' | 'search'
export function CommunicationTabs({
  tab,
  onChange,
}: {
  tab: CommunicationTab
  onChange: (tab: CommunicationTab) => void
}) {
  return (
    <nav
      aria-label="Espaces de discussion"
      className="flex shrink-0 gap-1 overflow-x-auto border-b bg-white p-2 text-[#1a1a1a]"
    >
      {(
        [
          ['team', 'Équipe'],
          ['plans', 'Plans d’action'],
          ['mentions', 'Mentions'],
          ['search', 'Rechercher'],
        ] as const
      ).map(([key, label]) => (
        <button
          key={key}
          type="button"
          aria-current={tab === key ? 'page' : undefined}
          onClick={() => onChange(key)}
          className={`whitespace-nowrap rounded-full px-3 py-2 text-sm font-semibold ${tab === key ? 'bg-[#114660] text-white' : 'bg-[#F5F4F0] text-[#1a1a1a]'}`}
        >
          {label}
        </button>
      ))}
    </nav>
  )
}
export function workspaceHref(establishmentId: string, item: WorkspaceItem) {
  return item.kind === 'plan'
    ? `/e/${establishmentId}/execution/${item.parent_id}?tab=comments&commentId=${item.id}`
    : `/e/${establishmentId}/chat/${item.parent_id}?messageId=${item.id}`
}
export function CommunicationWorkspace({
  establishmentId,
  tab,
}: {
  establishmentId: string
  tab: Exclude<CommunicationTab, 'team'>
}) {
  const { navigate } = useAppRoute()
  const [draft, setDraft] = useState('')
  const [query, setQuery] = useState('')
  const [unresolved, setUnresolved] = useState(false)
  const [author, setAuthor] = useState('')
  const [date, setDate] = useState('')
  const [files, setFiles] = useState(false)
  const people = useEligibleChatMembershipsQuery(establishmentId, '', { enabled: tab === 'search' })
  const filters: WorkspaceFilter = {
    tab,
    q: query,
    unresolved,
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
  return (
    <div className="min-h-0 flex-1 overflow-y-auto bg-white p-4 text-[#1a1a1a]">
      <div className="mx-auto max-w-3xl space-y-4">
        <h2 className="text-xl font-bold">
          {tab === 'plans'
            ? 'Discussions des plans'
            : tab === 'mentions'
              ? 'Les messages qui vous mentionnent'
              : 'Retrouver une information'}
        </h2>
        {tab === 'plans' && (
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={unresolved}
              onChange={(e) => setUnresolved(e.target.checked)}
            />{' '}
            Discussions non résolues uniquement
          </label>
        )}
        {tab === 'search' && (
          <form
            className="space-y-3"
            onSubmit={(e) => {
              e.preventDefault()
              setQuery(draft.trim())
            }}
          >
            <div className="flex gap-2">
              <Input
                aria-label="Rechercher dans les messages"
                placeholder="Devis, livraison, affiches…"
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
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
                  onChange={(e) => setAuthor(e.target.value)}
                  className="rounded border bg-white p-2"
                >
                  <option value="">Tous</option>
                  {people.data?.items.map((p) => (
                    <option key={p.membership_id} value={p.membership_id}>
                      {p.display_name}
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
                  onChange={(e) => setDate(e.target.value)}
                  className="rounded border p-2"
                />
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={files}
                  onChange={(e) => setFiles(e.target.checked)}
                />{' '}
                Avec pièce jointe
              </label>
            </div>
          </form>
        )}
        {results.isLoading && <p role="status">Chargement…</p>}
        {results.isError && (
          <div role="alert">
            <p>Impossible de charger les échanges.</p>
            <Button variant="outline" onClick={() => void results.refetch()}>
              Réessayer
            </Button>
          </div>
        )}
        {results.isSuccess && items.length === 0 && <p>Aucun échange à afficher.</p>}
        <ul className="space-y-2">
          {items.map((item) => (
            <li key={`${item.kind}-${item.id}`}>
              <button
                className="w-full rounded-2xl border border-[#D8D8D2] bg-white p-4 text-left hover:bg-[#F5F4F0]"
                onClick={() => navigate(workspaceHref(establishmentId, item))}
              >
                <div className="flex gap-2 font-semibold">
                  {item.unread && <span className="text-[#114660]">●</span>}
                  {item.title}
                </div>
                <p className="mt-1 text-xs text-[#4d4d47]">
                  {item.author} · {new Date(item.created_at).toLocaleString('fr-FR')} ·{' '}
                  {item.kind === 'plan' ? 'Plan' : 'Équipe'}
                </p>
                <p className="mt-2 line-clamp-3 whitespace-pre-wrap">
                  {item.body || 'Pièce jointe'}
                </p>
              </button>
            </li>
          ))}
        </ul>
        {results.hasNextPage && (
          <Button
            variant="outline"
            disabled={results.isFetchingNextPage}
            onClick={() => void results.fetchNextPage()}
          >
            Afficher la suite
          </Button>
        )}
      </div>
    </div>
  )
}
