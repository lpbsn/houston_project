import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { TerrainDialog } from '@/components/ui/terrain/terrain-dialog'
import { Button } from '@/components/ui/button'
import {
  recordKeys,
  updateRecord,
  type FieldRecord,
  type RecordStage,
  type RecordUpdate,
} from './api'

export const stages: { id: RecordStage; label: string }[] = [
  { id: 'todo', label: 'À traiter' },
  { id: 'doing', label: 'En cours' },
  { id: 'review', label: 'À vérifier' },
  { id: 'closed', label: 'Clos' },
]
export const inputClass =
  'w-full rounded-xl border border-[#C9CEC8] bg-white p-3 text-sm text-[#17251F] focus:outline-2 focus:outline-[#075940]'
export const panelClass =
  'rounded-2xl border border-[#DADFD8] bg-white p-5 text-[#17251F] shadow-sm'
export const dateLabel = (value: string) =>
  new Intl.DateTimeFormat('fr-FR', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    timeZone: 'UTC',
  }).format(new Date(`${value}T12:00:00Z`))
export function ErrorNote({ error }: { error: unknown }) {
  return error ? (
    <p
      role="alert"
      className="rounded-xl border border-red-300 bg-red-50 p-3 text-sm text-red-900"
    >
      {error instanceof Error ? error.message : 'Une erreur est survenue.'}
    </p>
  ) : null
}
export function useRecordUpdate(site: string, id: string) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (body: RecordUpdate) => updateRecord(site, id, body),
    onSuccess: async () => {
      await client.invalidateQueries({ queryKey: recordKeys.all(site) })
      void client.invalidateQueries({ queryKey: ['signals'] })
      void client.invalidateQueries({ queryKey: ['my-day'] })
    },
  })
}
export function CloseRecordDialog({
  site,
  record,
  onClose,
}: {
  site: string
  record: FieldRecord
  onClose: () => void
}) {
  const [reason, setReason] = useState<
    'resolved' | 'acknowledged' | 'abandoned'
  >('resolved')
  const mutation = useRecordUpdate(site, record.id)
  return (
    <TerrainDialog
      open
      title="Clore cette fiche"
      description="Le travail terminé ne prouve pas à lui seul la disparition du problème."
      onClose={onClose}
      dismissible={!mutation.isPending}
    >
      <label className="grid gap-2 text-sm font-medium">
        Quel résultat avez-vous constaté ?
        <select
          className={inputClass}
          value={reason}
          onChange={(e) => setReason(e.target.value as typeof reason)}
        >
          <option value="resolved">Le problème est résolu</option>
          <option value="acknowledged">
            L’information est prise en compte, sans action nécessaire
          </option>
          <option value="abandoned">Le sujet est abandonné</option>
        </select>
      </label>
      <ErrorNote error={mutation.error} />
      <Button
        className="mt-4"
        disabled={mutation.isPending}
        onClick={() =>
          mutation.mutate(
            {
              expected_updated_at: record.updated_at,
              stage: 'closed',
              closure_reason: reason,
            },
            { onSuccess: onClose },
          )
        }
      >
        Confirmer la clôture
      </Button>
    </TerrainDialog>
  )
}
