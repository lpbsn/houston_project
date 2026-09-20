import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  listPlatformOnboardings,
  platformQueryKeys,
  startPlatformOnboarding,
} from '@/features/platform/api'
import { PlatformListToolbar } from '@/features/platform/components/platform-list-toolbar'
import { formatFunctionalStatus } from '@/features/platform/lib/functional-status'
import { usePlatformListSearch } from '@/features/platform/lib/platform-search'
import { getCompleteErrorMessage } from '@/features/onboarding/lib/onboarding-draft-errors'

export function PlatformOnboardingsPage() {
  const queryClient = useQueryClient()
  const { q, replaceParams, navigate } = usePlatformListSearch('/platform/onboardings')
  const listQuery = useQuery({
    queryKey: platformQueryKeys.onboardings(q),
    queryFn: () => listPlatformOnboardings(q),
  })
  const [organizationName, setOrganizationName] = useState('')
  const [establishmentName, setEstablishmentName] = useState('')
  const [formError, setFormError] = useState<string | null>(null)
  const startMutation = useMutation({
    mutationFn: startPlatformOnboarding,
    onSuccess: async (created) => {
      await queryClient.invalidateQueries({ queryKey: platformQueryKeys.all })
      navigate(`/platform/onboardings/${created.id}`)
    },
    onError: (error) => {
      setFormError(getCompleteErrorMessage(error, 'Impossible de démarrer l’onboarding.'))
    },
  })

  return (
    <div>
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold">Onboardings</h2>
          <p className="mt-1 text-sm text-slate-600">
            Démarrer, reprendre et finaliser les configurations d’établissement.
          </p>
        </div>
      </div>

      <form
        className="mb-8 grid max-w-xl gap-3 rounded-xl border border-slate-200 bg-white p-4"
        onSubmit={(event) => {
          event.preventDefault()
          setFormError(null)
          startMutation.mutate({
            organization_name: organizationName.trim(),
            establishment_name: establishmentName.trim() || null,
          })
        }}
      >
        <p className="text-sm font-medium">Nouvel onboarding</p>
        <Input
          required
          value={organizationName}
          onChange={(event) => setOrganizationName(event.target.value)}
          placeholder="Nom de l’organisation"
        />
        <Input
          value={establishmentName}
          onChange={(event) => setEstablishmentName(event.target.value)}
          placeholder="Nom de l’établissement (optionnel)"
        />
        {formError ? <p className="text-sm text-red-600">{formError}</p> : null}
        <Button type="submit" disabled={startMutation.isPending || !organizationName.trim()}>
          Démarrer
        </Button>
      </form>

      <PlatformListToolbar
        q={q}
        onQueryChange={(value) => replaceParams({ q: value })}
        placeholder="Organisation ou établissement"
      />

      {listQuery.isPending ? <p className="text-sm text-slate-500">Chargement…</p> : null}
      {listQuery.error ? (
        <p className="text-sm text-red-600">Impossible de charger les onboardings.</p>
      ) : null}
      <ul className="divide-y divide-slate-200 rounded-xl border border-slate-200 bg-white">
        {(listQuery.data?.results ?? []).map((item) => (
          <li key={item.id}>
            <button
              type="button"
              className="flex w-full items-center justify-between px-4 py-3 text-left hover:bg-slate-50"
              onClick={() => navigate(`/platform/onboardings/${item.id}`)}
            >
              <span>
                <span className="block font-medium">{item.organization_name}</span>
                <span className="text-sm text-slate-500">{item.establishment_name ?? '—'}</span>
              </span>
              <span className="text-sm text-slate-600">
                {formatFunctionalStatus(item.functional_status)}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}
