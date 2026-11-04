import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { TerrainDialog } from '@/components/ui/terrain/terrain-dialog'
import {
  planRecord,
  recordKeys,
  type FieldRecord,
  type PlanningResponse,
} from './api'
import { dateLabel, ErrorNote, inputClass } from './shared'

export type PlanningDraft = { record: FieldRecord; start: string; due: string }
export function PlanningDialog({
  site,
  draft,
  onClose,
}: {
  site: string
  draft: PlanningDraft
  onClose: () => void
}) {
  const [start, setStart] = useState(draft.start)
  const [due, setDue] = useState(draft.due)
  const [preview, setPreview] = useState<PlanningResponse | null>(null)
  const client = useQueryClient()
  const mutation = useMutation({
    mutationFn: (apply: boolean) =>
      planRecord(site, draft.record.id, {
        expected_updated_at: draft.record.updated_at,
        start_on: draft.record.is_milestone ? due : start,
        due_on: due,
        apply,
        ...(apply && preview ? { expected_versions: preview.versions } : {}),
      }),
    onSuccess: async (result) => {
      if (!result.applied) {
        setPreview(result)
        return
      }
      await client.invalidateQueries({ queryKey: recordKeys.all(site) })
      void client.invalidateQueries({ queryKey: ['signals'] })
      void client.invalidateQueries({ queryKey: ['my-day'] })
      onClose()
    },
    onError: () => {
      setPreview(null)
      void client.invalidateQueries({ queryKey: recordKeys.all(site) })
    },
  })
  return (
    <TerrainDialog
      open
      title="Planifier la fiche"
      description={draft.record.title}
      onClose={onClose}
      dismissible={!mutation.isPending}
    >
      <form
        className="space-y-5 text-[#17251F]"
        onSubmit={(e) => {
          e.preventDefault()
          mutation.mutate(Boolean(preview))
        }}
      >
        <div className="grid gap-4 sm:grid-cols-2">
          {!draft.record.is_milestone && (
            <label className="grid gap-2 text-sm font-medium">
              Début planifié
              <input
                required
                type="date"
                className={inputClass}
                value={start}
                onChange={(e) => {
                  setStart(e.target.value)
                  setPreview(null)
                }}
              />
            </label>
          )}
          <label className="grid gap-2 text-sm font-medium">
            {draft.record.is_milestone ? 'Date du jalon' : 'Échéance'}
            <input
              required
              type="date"
              className={inputClass}
              value={due}
              onChange={(e) => {
                setDue(e.target.value)
                setPreview(null)
              }}
            />
          </label>
        </div>
        <p className="text-sm leading-relaxed text-[#45564A]">
          La date de création est conservée. Les fiches suivantes sont décalées
          uniquement si leur préalable finit trop tard. Les tâches des plans
          gardent leurs propres dates.
        </p>
        {preview && (
          <div
            className="rounded-xl border border-[#B5C7B8] bg-[#F2F7F0] p-4"
            aria-live="polite"
          >
            <h3 className="font-semibold">
              {preview.changes.length} fiche
              {preview.changes.length > 1 ? 's' : ''} à modifier
            </h3>
            <ul className="mt-3 max-h-64 space-y-3 overflow-y-auto">
              {preview.changes.map((row) => (
                <li
                  key={row.id}
                  className="border-t border-[#D5DFD2] pt-3 text-sm"
                >
                  <strong className="block">{row.title}</strong>
                  <span className="mt-1 block text-[#45564A]">
                    {dateLabel(row.before_start)} →{' '}
                    {row.before_due
                      ? dateLabel(row.before_due)
                      : 'sans échéance'}
                  </span>
                  <span className="block font-medium">
                    {dateLabel(row.start_on)} → {dateLabel(row.due_on)}
                  </span>
                </li>
              ))}
            </ul>
            {!preview.changes.length && (
              <p className="mt-2 text-sm">Aucune date ne change.</p>
            )}
          </div>
        )}
        <ErrorNote error={mutation.error} />
        <div className="flex justify-end gap-2">
          <Button
            variant="outline"
            type="button"
            disabled={mutation.isPending}
            onClick={onClose}
          >
            Annuler
          </Button>
          <Button
            type="submit"
            disabled={
              mutation.isPending || Boolean(preview && !preview.changes.length)
            }
          >
            {mutation.isPending
              ? 'Vérification…'
              : preview
                ? 'Confirmer les modifications'
                : 'Vérifier l’impact'}
          </Button>
        </div>
      </form>
    </TerrainDialog>
  )
}
