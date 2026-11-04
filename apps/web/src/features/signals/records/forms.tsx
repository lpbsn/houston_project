import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { TerrainDialog } from '@/components/ui/terrain/terrain-dialog'
import {
  commandRecord,
  recordKeys,
  recordOptions,
  type FieldRecord,
  type RecordCommand,
} from './api'
import { ErrorNote, inputClass, useRecordUpdate } from './shared'

export function RecordForm({
  site,
  record,
  kind,
  onClose,
}: {
  site: string
  record: FieldRecord
  kind: 'details' | 'work' | 'participants' | 'objective' | 'link'
  onClose: () => void
}) {
  const [choice, setChoice] = useState('')
  const [search, setSearch] = useState('')
  const options = useQuery({
    queryKey: ['field-record-options', site, search],
    queryFn: () => recordOptions(site, search),
  })
  const [title, setTitle] = useState(kind === 'work' ? '' : record.title)
  const [owner, setOwner] = useState(record.owner?.id ?? '')
  const [due, setDue] = useState(record.due_on ?? '')
  const [blocked, setBlocked] = useState(record.blocked_reason)
  const [waiting, setWaiting] = useState(record.waiting_for?.id ?? '')
  const [tasks, setTasks] = useState('')
  const [selected, setSelected] = useState(
    record.participants?.map((p) => p.id) ?? [],
  )
  const [quick, setQuick] = useState(true)
  const update = useRecordUpdate(site, record.id)
  const client = useQueryClient()
  const command = useMutation({
    mutationFn: (body: RecordCommand) => commandRecord(site, record.id, body),
    onSuccess: async () => {
      await client.invalidateQueries({ queryKey: recordKeys.all(site) })
      onClose()
    },
  })
  const busy = update.isPending || command.isPending
  const members = [
    ...(record.owner ? [record.owner] : []),
    ...(options.data?.members ?? []).filter((m) => m.id !== record.owner?.id),
  ]
  return (
    <TerrainDialog
      open
      title={
        kind === 'details'
          ? 'Organiser la fiche'
          : kind === 'work'
            ? 'Ajouter du travail'
            : kind === 'objective'
              ? 'Rattacher un objectif Brain'
              : kind === 'link'
                ? 'Rattacher un plan existant'
                : 'Participants'
      }
      onClose={onClose}
      dismissible={!busy}
    >
      <form
        className="grid gap-4"
        onSubmit={(e) => {
          e.preventDefault()
          if (kind === 'objective')
            command.mutate({
              expected_updated_at: record.updated_at,
              command: 'link_objective',
              objective_id: choice,
            })
          else if (kind === 'link')
            command.mutate({
              expected_updated_at: record.updated_at,
              command: 'link_work',
              execution_id: choice,
            })
          else if (kind === 'details')
            update.mutate(
              {
                expected_updated_at: record.updated_at,
                title,
                owner_membership_id: owner || null,
                due_on: due || null,
                blocked_reason: blocked,
                waiting_for_membership_id: waiting || null,
              },
              { onSuccess: onClose },
            )
          else if (kind === 'participants')
            command.mutate({
              expected_updated_at: record.updated_at,
              command: 'participants',
              membership_ids: selected,
            })
          else
            command.mutate({
              expected_updated_at: record.updated_at,
              command: 'work',
              title,
              assignee_id: owner || null,
              due_on: due || null,
              quick,
              tasks: tasks
                .split('\n')
                .map((t) => t.trim())
                .filter(Boolean),
            })
        }}
      >
        <label className="grid gap-1 text-sm">
          Rechercher
          <input
            className={inputClass}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Prénom ou nom…"
          />
        </label>
        {options.data?.more_members && (
          <p className="text-sm text-[#45564A]">
            Affinez la recherche pour trouver les autres membres.
          </p>
        )}
        {kind === 'objective' || kind === 'link' ? (
          <label className="grid gap-2 text-sm">
            {kind === 'objective' ? 'Objectif' : 'Plan'}
            <select
              required
              className={inputClass}
              value={choice}
              onChange={(e) => setChoice(e.target.value)}
            >
              <option value="">Choisir…</option>
              {(kind === 'objective'
                ? options.data?.objectives
                : options.data?.executions
              )?.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.name}
                </option>
              ))}
            </select>
            <span>
              Recherchez par titre. Le rattachement conserve le travail et son
              historique.
            </span>
          </label>
        ) : kind === 'participants' ? (
          <div className="max-h-60 space-y-2 overflow-y-auto">
            {members.map((m) => (
              <label key={m.id} className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={selected.includes(m.id)}
                  onChange={(e) =>
                    setSelected(
                      e.target.checked
                        ? [...selected, m.id]
                        : selected.filter((id) => id !== m.id),
                    )
                  }
                />
                {m.name}
              </label>
            ))}
          </div>
        ) : (
          <>
            <label className="grid gap-2 text-sm">
              {kind === 'details' ? 'Titre' : 'Nom du travail (facultatif)'}
              <input
                required={kind === 'details'}
                maxLength={200}
                className={inputClass}
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />
            </label>
            <label className="grid gap-2 text-sm">
              {kind === 'details'
                ? 'Responsable de la fiche'
                : 'Personne assignée'}
              <select
                required={kind === 'work'}
                className={inputClass}
                value={owner}
                onChange={(e) => setOwner(e.target.value)}
              >
                <option value="">À définir</option>
                {members.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="grid gap-2 text-sm">
              Échéance
              <input
                className={inputClass}
                type="date"
                value={due}
                onChange={(e) => setDue(e.target.value)}
              />
            </label>
            {kind === 'details' ? (
              <>
                <label className="grid gap-2 text-sm">
                  Blocage (vide si aucun)
                  <textarea
                    maxLength={500}
                    className={inputClass}
                    value={blocked}
                    onChange={(e) => setBlocked(e.target.value)}
                  />
                </label>
                <label className="grid gap-2 text-sm">
                  En attente de
                  <select
                    className={inputClass}
                    value={waiting}
                    onChange={(e) => setWaiting(e.target.value)}
                  >
                    <option value="">Personne en particulier</option>
                    {members.map((m) => (
                      <option key={m.id} value={m.id}>
                        {m.name}
                      </option>
                    ))}
                  </select>
                </label>
              </>
            ) : (
              <>
                <label className="grid gap-2 text-sm">
                  Tâches · une par ligne
                  <textarea
                    className={inputClass}
                    rows={5}
                    value={tasks}
                    onChange={(e) => setTasks(e.target.value)}
                  />
                </label>
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={quick}
                    onChange={(e) => setQuick(e.target.checked)}
                  />
                  Ajouter aux tâches de la fiche
                </label>
                <p className="text-xs text-[#45564A]">
                  Décochez pour créer un plan d’action distinct dans cette
                  fiche.
                </p>
              </>
            )}
          </>
        )}
        <ErrorNote error={update.error ?? command.error ?? options.error} />
        <Button type="submit" disabled={busy}>
          Enregistrer
        </Button>
      </form>
    </TerrainDialog>
  )
}
