import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { Button } from '@/components/ui/button'
import {
  activatePlatformKnowledgeVersion,
  brainQueryKeys,
  decidePlatformMechanism,
  listPlatformKnowledgeVersions,
  listPlatformMechanisms,
} from '@/features/brain/api'
import { errorDetail } from '@/features/brain/display'

export function PlatformKnowledgePage() {
  const queryClient = useQueryClient()
  const mechanisms = useQuery({
    queryKey: brainQueryKeys.platformMechanisms,
    queryFn: listPlatformMechanisms,
  })
  const versions = useQuery({
    queryKey: brainQueryKeys.platformVersions,
    queryFn: listPlatformKnowledgeVersions,
  })

  function refresh() {
    void queryClient.invalidateQueries({ queryKey: brainQueryKeys.platformMechanisms })
    void queryClient.invalidateQueries({ queryKey: brainQueryKeys.platformVersions })
  }

  return (
    <div className="flex flex-col gap-8">
      <header>
        <h1 className="text-2xl font-semibold">Knowledge</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          L&apos;approbation crée une version inactive. L&apos;activation est une action séparée.
          Les dossiers privés des établissements ne sont pas chargés.
        </p>
      </header>
      <section>
        <h2 className="text-lg font-medium">Candidats</h2>
        {mechanisms.error ? <p className="mt-2 text-sm">{errorDetail(mechanisms.error)}</p> : null}
        <div className="mt-3 flex flex-col gap-4">
          {(mechanisms.data?.results ?? []).map((candidate) => (
            <MechanismReview key={candidate.id} candidateId={candidate.id} candidate={candidate} onChanged={refresh} />
          ))}
        </div>
      </section>
      <section>
        <h2 className="text-lg font-medium">Versions</h2>
        <ul className="mt-3 flex flex-col gap-3 text-sm">
          {(versions.data?.results ?? []).map((version) => (
            <li key={version.id} className="rounded-lg border border-border p-3">
              <p>{version.formulation}</p>
              <p className="mt-1 text-muted-foreground">
                {version.is_active ? 'Active' : 'Inactive'}
                {version.approved_at ? ` — approuvée` : ''}
                {version.activated_at ? ` — activée` : ''}
              </p>
              {!version.is_active ? (
                <ActivateVersion versionId={version.id} onChanged={refresh} />
              ) : null}
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}

function MechanismReview({
  candidateId,
  candidate,
  onChanged,
}: {
  candidateId: string
  candidate: {
    status: string
    is_active: boolean
    knowledge_version_id: string | null
    representation: {
      formulation: string
      conditions: string
      limits: string
      uncertainty: string
      withheld: { [key: string]: unknown }
    }
  }
  onChanged: () => void
}) {
  const decide = useMutation({
    mutationFn: (decision: 'approve' | 'reject') => decidePlatformMechanism(candidateId, decision),
    onSuccess: onChanged,
  })
  const withheld = Object.keys(candidate.representation.withheld)
  return (
    <article className="rounded-lg border border-border p-3 text-sm">
      <p>Statut : {candidate.status}</p>
      <p className="mt-2">{candidate.representation.formulation}</p>
      {candidate.representation.conditions ? <p className="mt-1">{candidate.representation.conditions}</p> : null}
      {candidate.representation.limits ? <p className="mt-1">{candidate.representation.limits}</p> : null}
      {candidate.representation.uncertainty ? <p className="mt-1">{candidate.representation.uncertainty}</p> : null}
      {withheld.length > 0 ? (
        <p className="mt-2">Des éléments restent privés et ne sont pas affichés.</p>
      ) : null}
      {candidate.knowledge_version_id && !candidate.is_active ? (
        <p className="mt-2">Version approuvée, pas encore activée.</p>
      ) : null}
      {decide.error ? <p className="mt-2">{errorDetail(decide.error)}</p> : null}
      <div className="mt-3 flex gap-2">
        <Button type="button" onClick={() => decide.mutate('approve')} disabled={decide.isPending}>
          Approuver
        </Button>
        <Button type="button" variant="outline" onClick={() => decide.mutate('reject')} disabled={decide.isPending}>
          Refuser
        </Button>
      </div>
    </article>
  )
}

function ActivateVersion({ versionId, onChanged }: { versionId: string; onChanged: () => void }) {
  const activate = useMutation({
    mutationFn: () => activatePlatformKnowledgeVersion(versionId),
    onSuccess: onChanged,
  })
  return (
    <div className="mt-2">
      <Button type="button" variant="outline" disabled={activate.isPending} onClick={() => activate.mutate()}>
        Activer
      </Button>
      {activate.error ? <p className="mt-2">{errorDetail(activate.error)}</p> : null}
    </div>
  )
}
