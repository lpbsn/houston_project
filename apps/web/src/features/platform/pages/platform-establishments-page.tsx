import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { getCompleteErrorMessage } from '@/features/onboarding/lib/onboarding-draft-errors'
import {
  deletePlatformEstablishment,
  getPlatformEstablishment,
  listPlatformEstablishments,
  platformQueryKeys,
} from '@/features/platform/api'
import { PlatformListToolbar } from '@/features/platform/components/platform-list-toolbar'
import { formatFunctionalStatus } from '@/features/platform/lib/functional-status'
import { usePlatformListSearch } from '@/features/platform/lib/platform-search'

export function PlatformEstablishmentsPage({ resourceId }: { resourceId?: string }) {
  if (resourceId) {
    return <PlatformEstablishmentDetailGate establishmentId={resourceId} />
  }
  return <PlatformEstablishmentsList />
}

function PlatformEstablishmentDetailGate({ establishmentId }: { establishmentId: string }) {
  const { navigate } = usePlatformListSearch('/platform/establishments')
  return (
    <PlatformEstablishmentDetailPage establishmentId={establishmentId} onNavigate={navigate} />
  )
}

function PlatformEstablishmentsList() {
  const { q, replaceParams, navigate } = usePlatformListSearch('/platform/establishments')

  const listQuery = useQuery({
    queryKey: platformQueryKeys.establishments(q),
    queryFn: () => listPlatformEstablishments(q),
  })

  return (
    <div>
      <h2 className="mb-2 text-2xl font-semibold">Établissements</h2>
      <p className="mb-6 text-sm text-slate-600">Diagnostic d’état fonctionnel, sans wizard.</p>
      <PlatformListToolbar
        q={q}
        onQueryChange={(value) => replaceParams({ q: value })}
        placeholder="Nom d’établissement"
      />
      {listQuery.isPending ? <p className="text-sm text-slate-500">Chargement…</p> : null}
      <ul className="divide-y divide-slate-200 rounded-xl border border-slate-200 bg-white">
        {(listQuery.data?.results ?? []).map((item) => (
          <li key={item.id}>
            <button
              type="button"
              className="flex w-full items-center justify-between px-4 py-3 text-left hover:bg-slate-50"
              onClick={() => navigate(`/platform/establishments/${item.id}`)}
            >
              <span>
                <span className="block font-medium">{item.name ?? item.id}</span>
                <span className="text-sm text-slate-500">{item.organization_name}</span>
              </span>
              <span className="text-sm text-slate-600">
                {formatFunctionalStatus(item.onboarding.functional_status)}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}

function PlatformEstablishmentDetailPage({
  establishmentId,
  onNavigate,
}: {
  establishmentId: string
  onNavigate: (path: string) => void
}) {
  const queryClient = useQueryClient()
  const detailQuery = useQuery({
    queryKey: platformQueryKeys.establishment(establishmentId),
    queryFn: () => getPlatformEstablishment(establishmentId),
  })
  const [justification, setJustification] = useState('')
  const [error, setError] = useState<string | null>(null)
  const deleteMutation = useMutation({
    mutationFn: () => deletePlatformEstablishment(establishmentId, justification.trim()),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: platformQueryKeys.all })
      onNavigate('/platform/establishments')
    },
    onError: (caught) => {
      setError(getCompleteErrorMessage(caught, 'Suppression refusée.'))
    },
  })
  const detail = detailQuery.data

  return (
    <div>
      <button
        type="button"
        className="mb-4 text-sm text-slate-600 hover:underline"
        onClick={() => onNavigate('/platform/establishments')}
      >
        ← Établissements
      </button>
      {detail ? (
        <div className="max-w-2xl space-y-4">
          <h2 className="text-2xl font-semibold">{detail.name ?? detail.id}</h2>
          <p className="text-sm text-slate-600">{detail.organization_name}</p>
          <p className="rounded-xl border border-slate-200 bg-white p-4 text-sm">
            État fonctionnel : {formatFunctionalStatus(detail.onboarding.functional_status)}
          </p>
          {detail.onboarding.session_id && detail.onboarding.functional_status !== 'activated' ? (
            <Button
              type="button"
              onClick={() => onNavigate(`/platform/onboardings/${detail.onboarding.session_id}`)}
            >
              Ouvrir le wizard
            </Button>
          ) : null}
          {detail.can_delete ? (
            <form
              className="space-y-3 rounded-xl border border-slate-200 bg-white p-4"
              onSubmit={(event) => {
                event.preventDefault()
                setError(null)
                deleteMutation.mutate()
              }}
            >
              <p className="text-sm font-medium">Supprimer (abandon)</p>
              <Input
                required
                value={justification}
                onChange={(event) => setJustification(event.target.value)}
                placeholder="Justification"
              />
              {error ? <p className="text-sm text-red-600">{error}</p> : null}
              <Button type="submit" variant="destructive" disabled={deleteMutation.isPending}>
                Supprimer l’établissement
              </Button>
            </form>
          ) : (
            <p className="text-sm text-slate-500">
              Suppression impossible
              {detail.blocking_reasons.length > 0
                ? ` : ${detail.blocking_reasons.join(', ')}`
                : '.'}
            </p>
          )}
        </div>
      ) : null}
    </div>
  )
}
