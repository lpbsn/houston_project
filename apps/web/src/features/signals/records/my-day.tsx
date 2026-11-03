import { useInfiniteQuery } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { listRecords, recordKeys } from './api'
import { dateLabel, ErrorNote } from './shared'

export function MyDayRecords({
  site,
  onNavigate,
}: {
  site: string
  onNavigate: (path: string) => void
}) {
  const query = useInfiniteQuery({
    queryKey: [...recordKeys.all(site), 'day'],
    initialPageParam: 0,
    queryFn: ({ pageParam }) => listRecords(site, { day: true }, pageParam),
    getNextPageParam: (page) => page.next_offset ?? undefined,
  })
  const records = query.data?.pages.flatMap((p) => p.items) ?? []
  return (
    <section className="space-y-3 rounded-2xl border border-[#DADFD8] bg-white p-5 text-[#17251F]">
      <h3 className="font-semibold">Mes fiches et les résultats à vérifier</h3>
      <ErrorNote error={query.error} />
      {query.isPending && <p role="status">Chargement…</p>}
      {records.map((record) => (
        <button
          key={record.id}
          className="block w-full rounded-xl bg-[#EFF4EC] p-3 text-left"
          onClick={() => onNavigate(`/e/${site}/signals/${record.id}`)}
        >
          <span className="font-medium">{record.title}</span>
          <span className="mt-1 block text-sm text-[#45564A]">
            {record.stage === 'review'
              ? 'Résultat à vérifier'
              : record.due_on
                ? dateLabel(record.due_on)
                : 'Sans échéance'}
            {record.blocked_reason ? ' · Bloqué' : ''}
          </span>
        </button>
      ))}
      {!query.isPending && !query.isError && records.length === 0 && (
        <p className="text-sm text-[#45564A]">
          Aucune fiche supplémentaire à suivre.
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
    </section>
  )
}
