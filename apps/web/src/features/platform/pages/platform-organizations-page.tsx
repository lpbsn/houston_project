import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { getCompleteErrorMessage } from '@/features/onboarding/lib/onboarding-draft-errors'
import {
  deletePlatformOrganization,
  getPlatformOrganization,
  listPlatformOrganizations,
  platformQueryKeys,
} from '@/features/platform/api'
import { PlatformListToolbar } from '@/features/platform/components/platform-list-toolbar'
import { usePlatformListSearch } from '@/features/platform/lib/platform-search'

export function PlatformOrganizationsPage({ resourceId }: { resourceId?: string }) {
  if (resourceId) {
    return <PlatformOrganizationDetailGate organizationId={resourceId} />
  }
  return <PlatformOrganizationsList />
}

function PlatformOrganizationDetailGate({ organizationId }: { organizationId: string }) {
  const { navigate } = usePlatformListSearch('/platform/organizations')
  return <PlatformOrganizationDetailPage organizationId={organizationId} onNavigate={navigate} />
}

function PlatformOrganizationsList() {
  const { q, replaceParams, navigate } = usePlatformListSearch('/platform/organizations')

  const listQuery = useQuery({
    queryKey: platformQueryKeys.organizations(q),
    queryFn: () => listPlatformOrganizations(q),
  })

  return (
    <div>
      <h2 className="mb-2 text-2xl font-semibold">Organisations</h2>
      <p className="mb-6 text-sm text-slate-600">Diagnostic et suppression d’abandon.</p>
      <PlatformListToolbar
        q={q}
        onQueryChange={(value) => replaceParams({ q: value })}
        placeholder="Nom d’organisation"
      />
      {listQuery.isPending ? <p className="text-sm text-slate-500">Chargement…</p> : null}
      <ul className="divide-y divide-slate-200 rounded-xl border border-slate-200 bg-white">
        {(listQuery.data?.results ?? []).map((item) => (
          <li key={item.id}>
            <button
              type="button"
              className="flex w-full items-center justify-between px-4 py-3 text-left hover:bg-slate-50"
              onClick={() => navigate(`/platform/organizations/${item.id}`)}
            >
              <span className="font-medium">{item.name}</span>
              <span className="text-sm text-slate-500">{item.status}</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}

function PlatformOrganizationDetailPage({
  organizationId,
  onNavigate,
}: {
  organizationId: string
  onNavigate: (path: string) => void
}) {
  const queryClient = useQueryClient()
  const detailQuery = useQuery({
    queryKey: platformQueryKeys.organization(organizationId),
    queryFn: () => getPlatformOrganization(organizationId),
  })
  const [justification, setJustification] = useState('')
  const [error, setError] = useState<string | null>(null)
  const deleteMutation = useMutation({
    mutationFn: () => deletePlatformOrganization(organizationId, justification.trim()),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: platformQueryKeys.all })
      onNavigate('/platform/organizations')
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
        onClick={() => onNavigate('/platform/organizations')}
      >
        ← Organisations
      </button>
      {detailQuery.isPending ? <p>Chargement…</p> : null}
      {detail ? (
        <div className="max-w-2xl space-y-4">
          <h2 className="text-2xl font-semibold">{detail.name}</h2>
          <p className="text-sm text-slate-600">
            Statut {detail.status} · opérationnelle {detail.has_been_operational ? 'oui' : 'non'}
          </p>
          <ul className="rounded-xl border border-slate-200 bg-white p-4 text-sm">
            {detail.establishments.map((establishment) => (
              <li key={establishment.id}>
                <button
                  type="button"
                  className="hover:underline"
                  onClick={() => onNavigate(`/platform/establishments/${establishment.id}`)}
                >
                  {establishment.name ?? establishment.id}
                </button>
              </li>
            ))}
          </ul>
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
                Supprimer l’organisation
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
