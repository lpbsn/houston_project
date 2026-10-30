import { useQuery } from '@tanstack/react-query'
import { useAppRoute } from '@/app/app-routes'
import { fetchSourceMessage } from '../workspace-api'
import { MessageBubble } from './message-bubble'
export function SourceMessage({
  establishmentId,
  conversationId,
}: {
  establishmentId: string
  conversationId: string
}) {
  const { search } = useAppRoute()
  const id = new URLSearchParams(search).get('messageId')
  const query = useQuery({
    queryKey: ['chat', 'source-message', establishmentId, id],
    queryFn: () => fetchSourceMessage(establishmentId, id!),
    enabled: Boolean(id),
  })
  if (!id) return null
  return (
    <section
      aria-label="Message recherché"
      className="mt-2 max-h-64 overflow-auto rounded-xl border-2 border-[#114660] p-3 text-[#1a1a1a]"
    >
      <p className="mb-2 font-semibold">Message recherché</p>
      {query.isLoading && <p>Chargement…</p>}
      {query.isError && <p role="alert">Ce message n’est plus accessible.</p>}
      {query.data && (
        <MessageBubble
          message={query.data}
          isOwn={false}
          establishmentId={establishmentId}
          conversationId={conversationId}
        />
      )}
    </section>
  )
}
