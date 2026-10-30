import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { TerrainDialog } from '@/components/ui/terrain'
import { fetchActionPlanExecutionDetail } from '@/features/action-plans/api'
import { commentTool } from '@/features/chat/workspace-api'
import type { ExecutionCommentListItem } from '../types'

export function CommentTools({
  establishmentId,
  executionId,
  item,
  disabled,
}: {
  establishmentId: string
  executionId: string
  item: ExecutionCommentListItem
  disabled?: boolean
}) {
  const client = useQueryClient()
  const [open, setOpen] = useState(false)
  const [title, setTitle] = useState('')
  const [assignee, setAssignee] = useState('')
  const [deadline, setDeadline] = useState('')
  const execution = useQuery({
    queryKey: ['chat', 'task-destination', establishmentId, executionId],
    queryFn: () => fetchActionPlanExecutionDetail(establishmentId, executionId),
    enabled: open,
  })
  const mutation = useMutation({
    mutationFn: (body: Parameters<typeof commentTool>[2]) =>
      commentTool(establishmentId, item.id, body),
    onSuccess: async (_, body) => {
      await Promise.all([
        client.invalidateQueries({
          queryKey: ['comments', 'action-plan-execution', establishmentId, executionId],
        }),
        client.invalidateQueries({ queryKey: ['action-plans'] }),
        client.invalidateQueries({ queryKey: ['chat', 'workspace', establishmentId] }),
      ])
      if (body.operation === 'task') setOpen(false)
    },
  })
  return (
    <div className="my-2 text-[#1a1a1a]">
      <div className="flex flex-wrap gap-2 text-xs">
        <button
          type="button"
          disabled={disabled || mutation.isPending}
          aria-pressed={item.acknowledged ?? false}
          onClick={() => mutation.mutate({ operation: 'acknowledge', active: !item.acknowledged })}
          className="rounded-full border bg-white px-3 py-1.5 text-[#114660]"
        >
          👍 {item.acknowledgement_count || ''}
        </button>
        {item.permission_hints?.can_resolve && (
          <button
            type="button"
            disabled={disabled || mutation.isPending}
            aria-pressed={item.pinned ?? false}
            onClick={() => mutation.mutate({ operation: 'pin', active: !item.pinned })}
            className="rounded-full border bg-white px-3 py-1.5 text-[#114660]"
          >
            {item.pinned ? 'Désépingler la décision' : 'Épingler la décision'}
          </button>
        )}
        {item.created_task_id ? (
          <span className="rounded-full bg-[#E8F0EF] px-3 py-1.5">Tâche créée dans ce plan</span>
        ) : (
          item.can_create_task && (
            <button
              type="button"
              disabled={disabled || mutation.isPending}
              onClick={() => {
                mutation.reset()
                setTitle(item.body)
                setOpen(true)
              }}
              className="rounded-full border bg-white px-3 py-1.5 text-[#114660]"
            >
              Créer une tâche
            </button>
          )
        )}
      </div>
      {mutation.isError && !open && <p role="alert">{mutation.error.message}</p>}
      <TerrainDialog
        open={open}
        title="Créer une tâche dans ce plan"
        onClose={() => setOpen(false)}
      >
        <div className="space-y-3 text-[#1a1a1a]">
          <p className="text-sm">
            Précisez l’action à réaliser. Le commentaire sera conservé dans sa description.
          </p>
          <label>
            Action
            <textarea
              aria-label="Action à réaliser"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              rows={3}
              className="w-full rounded border p-2"
            />
          </label>
          <label>
            Responsable
            <select
              aria-label="Responsable de la tâche"
              value={assignee}
              onChange={(e) => setAssignee(e.target.value)}
              className="w-full rounded border bg-white p-2"
            >
              <option value="">Partagée avec le pôle pilote</option>
              {execution.data?.assignees_by_pole.flatMap((p) =>
                p.assignees.map((a) => (
                  <option key={a.membership_id} value={a.membership_id}>
                    {a.display_name} · {p.business_unit.specific_name}
                  </option>
                )),
              )}
            </select>
          </label>
          <label>
            Échéance
            <input
              aria-label="Échéance de la tâche"
              type="datetime-local"
              value={deadline}
              onChange={(e) => setDeadline(e.target.value)}
              className="w-full rounded border p-2"
            />
          </label>
          <p className="text-xs text-[#4d4d47]">
            Heure locale de votre appareil. Modifiez les participants dans le plan si nécessaire.
          </p>
          {execution.isError && (
            <p role="alert">
              Impossible de charger les responsables.{' '}
              <button onClick={() => void execution.refetch()}>Réessayer</button>
            </p>
          )}
          {mutation.isError && <p role="alert">{mutation.error.message}</p>}
          <Button
            disabled={
              mutation.isPending || !execution.isSuccess || !title.trim() || title.length > 255
            }
            onClick={() =>
              mutation.mutate({
                operation: 'task',
                active: true,
                title,
                assigned_membership_id: assignee || null,
                deadline_at: deadline ? new Date(deadline).toISOString() : null,
              })
            }
          >
            Confirmer la création
          </Button>
        </div>
      </TerrainDialog>
    </div>
  )
}
