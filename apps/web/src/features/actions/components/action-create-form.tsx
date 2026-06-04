import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'

import { useAuth } from '@/app/auth-provider'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { TerrainFieldLabel } from '@/components/ui/terrain'
import { getOperationalTaxonomy, operationalTaxonomyQueryKey } from '@/features/auth/api'
import { searchEstablishmentUsers } from '@/features/actions/api'
import type { ActionCreateRequest } from '@/features/actions/types'

type ActionCreateFormProps = {
  initialSignalId?: string | null
  suggestedModuleKey?: string | null
  suggestedDomainKey?: string | null
  suggestedSubjectKey?: string | null
  onCancel: () => void
  onCreated: (actionId: string) => void
  onSubmit: (body: ActionCreateRequest) => Promise<{ id: string }>
  isSubmitting: boolean
  errorMessage?: string | null
}

export function ActionCreateForm({
  initialSignalId = null,
  suggestedModuleKey = null,
  suggestedDomainKey = null,
  suggestedSubjectKey = null,
  onCancel,
  onCreated,
  onSubmit,
  isSubmitting,
  errorMessage = null,
}: ActionCreateFormProps) {
  const auth = useAuth()
  const establishmentId = auth.bootstrap?.active_membership?.establishment_id ?? null

  const [title, setTitle] = useState('')
  const [instruction, setInstruction] = useState('')
  const [dueAt, setDueAt] = useState('')
  const [linkMode, setLinkMode] = useState<'free' | 'linked'>(
    initialSignalId ? 'linked' : 'free',
  )
  const [signalId, setSignalId] = useState(initialSignalId ?? '')
  const [moduleKey, setModuleKey] = useState(suggestedModuleKey ?? '')
  const [domainKey, setDomainKey] = useState(suggestedDomainKey ?? '')
  const [subjectKey, setSubjectKey] = useState(suggestedSubjectKey ?? '')
  const [assigneeQuery, setAssigneeQuery] = useState('')
  const [assignedTo, setAssignedTo] = useState('')

  const taxonomyQuery = useQuery({
    queryKey: establishmentId ? operationalTaxonomyQueryKey(establishmentId) : ['taxonomy', 'none'],
    queryFn: () => {
      if (!establishmentId) {
        throw new Error('Établissement non sélectionné.')
      }
      return getOperationalTaxonomy(establishmentId)
    },
    enabled: Boolean(establishmentId),
  })

  const domains = useMemo(() => {
    const modules = taxonomyQuery.data?.modules ?? []
    const mod = modules.find((m) => m.key === moduleKey)
    return mod?.domains ?? []
  }, [moduleKey, taxonomyQuery.data?.modules])

  const subjects = useMemo(() => {
    const domain = domains.find((d) => d.key === domainKey)
    return domain?.subjects ?? []
  }, [domainKey, domains])

  const usersQuery = useQuery({
    queryKey: ['users', 'search', establishmentId, assigneeQuery],
    queryFn: () => {
      if (!establishmentId || assigneeQuery.trim().length < 2) {
        return []
      }
      return searchEstablishmentUsers(establishmentId, assigneeQuery.trim())
    },
    enabled: Boolean(establishmentId) && assigneeQuery.trim().length >= 2,
  })

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!assignedTo || !dueAt) {
      return
    }
    const body: ActionCreateRequest = {
      title: title.trim(),
      instruction: instruction.trim(),
      assigned_to: assignedTo,
      due_at: new Date(dueAt).toISOString(),
      module_key: moduleKey,
      domain_key: domainKey,
      subject_key: subjectKey,
      signal: linkMode === 'linked' && signalId ? signalId : null,
    }
    const created = await onSubmit(body)
    onCreated(created.id)
  }

  return (
    <form className="flex flex-col gap-3" onSubmit={(e) => void handleSubmit(e)}>
      {!initialSignalId ? (
        <div className="flex gap-2">
          <Button
            type="button"
            variant={linkMode === 'free' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setLinkMode('free')}
          >
            Action libre
          </Button>
          <Button
            type="button"
            variant={linkMode === 'linked' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setLinkMode('linked')}
          >
            Liée à un signal
          </Button>
        </div>
      ) : null}
      {linkMode === 'linked' && !initialSignalId ? (
        <div>
          <TerrainFieldLabel>ID signal (UUID)</TerrainFieldLabel>
          <Input value={signalId} onChange={(e) => setSignalId(e.target.value)} className="mt-1" />
        </div>
      ) : null}
      <div>
        <TerrainFieldLabel>Titre</TerrainFieldLabel>
        <Input value={title} onChange={(e) => setTitle(e.target.value)} className="mt-1" required />
      </div>
      <div>
        <TerrainFieldLabel>Consigne</TerrainFieldLabel>
        <textarea
          className="mt-1 min-h-[80px] w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm"
          value={instruction}
          onChange={(e) => setInstruction(e.target.value)}
          required
        />
      </div>
      <div>
        <TerrainFieldLabel>Échéance</TerrainFieldLabel>
        <Input
          type="datetime-local"
          value={dueAt}
          onChange={(e) => setDueAt(e.target.value)}
          className="mt-1"
          required
        />
      </div>
      <div>
        <TerrainFieldLabel>Module</TerrainFieldLabel>
        <select
          className="mt-1 h-10 w-full rounded-md border border-input px-3 text-sm"
          value={moduleKey}
          onChange={(e) => {
            setModuleKey(e.target.value)
            setDomainKey('')
            setSubjectKey('')
          }}
          required
        >
          <option value="">Choisir…</option>
          {(taxonomyQuery.data?.modules ?? []).map((m) => (
            <option key={m.id} value={m.key}>
              {m.label}
            </option>
          ))}
        </select>
      </div>
      <div>
        <TerrainFieldLabel>Domaine</TerrainFieldLabel>
        <select
          className="mt-1 h-10 w-full rounded-md border border-input px-3 text-sm"
          value={domainKey}
          onChange={(e) => {
            setDomainKey(e.target.value)
            setSubjectKey('')
          }}
          required
          disabled={!moduleKey}
        >
          <option value="">Choisir…</option>
          {domains.map((d) => (
            <option key={d.id} value={d.key}>
              {d.label}
            </option>
          ))}
        </select>
      </div>
      <div>
        <TerrainFieldLabel>Sujet</TerrainFieldLabel>
        <select
          className="mt-1 h-10 w-full rounded-md border border-input px-3 text-sm"
          value={subjectKey}
          onChange={(e) => setSubjectKey(e.target.value)}
          required
          disabled={!domainKey}
        >
          <option value="">Choisir…</option>
          {subjects.map((s) => (
            <option key={s.id} value={s.key}>
              {s.label}
            </option>
          ))}
        </select>
      </div>
      <div>
        <TerrainFieldLabel>Assigné à</TerrainFieldLabel>
        <Input
          value={assigneeQuery}
          onChange={(e) => setAssigneeQuery(e.target.value)}
          placeholder="Rechercher (2 car. min.)"
          className="mt-1"
        />
        {usersQuery.data && usersQuery.data.length > 0 ? (
          <ul className="mt-1 max-h-32 overflow-auto rounded-md border border-[#E8E6DF] bg-white">
            {usersQuery.data.map((user) => (
              <li key={user.membership_id}>
                <button
                  type="button"
                  className={`w-full px-3 py-2 text-left text-sm hover:bg-[#F5F4F0] ${assignedTo === user.membership_id ? 'bg-[#E8F0FE]' : ''}`}
                  onClick={() => {
                    setAssignedTo(user.membership_id)
                    setAssigneeQuery(user.display_name)
                  }}
                >
                  {user.display_name}
                </button>
              </li>
            ))}
          </ul>
        ) : null}
      </div>
      {errorMessage ? (
        <p className="text-sm text-destructive" role="alert">
          {errorMessage}
        </p>
      ) : null}
      <div className="flex gap-2 pt-2">
        <Button type="button" variant="outline" className="flex-1" onClick={onCancel}>
          Annuler
        </Button>
        <Button type="submit" className="flex-1" disabled={isSubmitting}>
          {isSubmitting ? 'Création…' : 'Créer'}
        </Button>
      </div>
    </form>
  )
}
