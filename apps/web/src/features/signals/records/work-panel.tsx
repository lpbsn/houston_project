import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { CommentSection } from '@/features/comments/components/comment-section'
import { ActionPlanExecutionValidateRatingSheet } from '@/features/action-plans/components/action-plan-execution-validate-rating-sheet'
import {
  fetchActionPlanExecutionDetail,
  markActionPlanTaskDone,
  markActionPlanTaskPending,
  markActionPlanExecutionDone,
  validateActionPlanExecution,
} from '@/features/action-plans/api'
import { commandRecord, recordKeys, type FieldRecord } from './api'
import { ErrorNote, inputClass } from './shared'

export function RecordWorkPanel({
  site,
  executionId,
  record,
  onNavigate,
}: {
  site: string
  executionId: string
  record: FieldRecord
  onNavigate: (path: string) => void
}) {
  const client = useQueryClient()
  const query = useQuery({
    queryKey: ['action-plans', 'execution-detail', site, executionId],
    queryFn: () => fetchActionPlanExecutionDetail(site, executionId),
  })
  const [validating, setValidating] = useState(false)
  const [stars, setStars] = useState<number | null>(null)
  const [comment, setComment] = useState('')
  const refresh = async () => {
    await client.invalidateQueries({
      queryKey: ['action-plans', 'execution-detail', site, executionId],
    })
    await client.invalidateQueries({ queryKey: recordKeys.all(site) })
    void client.invalidateQueries({ queryKey: ['my-day'] })
  }
  const taskMutation = useMutation({
    mutationFn: ({ id, done }: { id: string; done: boolean }) =>
      done
        ? markActionPlanTaskDone(site, id)
        : markActionPlanTaskPending(site, id),
    onSuccess: refresh,
  })
  const doneMutation = useMutation({
    mutationFn: () => markActionPlanExecutionDone(site, executionId),
    onSuccess: refresh,
  })
  const dependency = useMutation({
    mutationFn: ({
      taskId,
      prerequisite,
    }: {
      taskId: string
      prerequisite: string | null
    }) =>
      commandRecord(site, record.id, {
        command: 'dependency',
        expected_updated_at: record.updated_at,
        execution_id: executionId,
        task_id: taskId,
        depends_on_id: prerequisite,
      }),
    onSuccess: refresh,
  })
  const validation = useMutation({
    mutationFn: () =>
      validateActionPlanExecution(site, executionId, {
        stars: stars!,
        comment,
      }),
    onSuccess: async () => {
      setValidating(false)
      await refresh()
    },
  })
  const execution = query.data
  if (!execution)
    return (
      <>
        <ErrorNote error={query.error} />
        {query.isPending && <p role="status">Chargement du travail…</p>}
      </>
    )
  const statuses: Record<string, string> = {
    in_progress: 'En cours',
    scheduled: 'Planifié',
    pending_validation: 'À valider',
    done: 'Terminé',
    canceled: 'Annulé',
  }
  return (
    <div className="space-y-4 rounded-xl border border-[#D5DDD2] bg-[#FAFCF8] p-4 text-[#17251F]">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-semibold">
          {statuses[execution.status] ?? execution.status}
        </p>
        <Button
          variant="outline"
          size="sm"
          onClick={() => onNavigate(`/e/${site}/execution/${executionId}`)}
        >
          Détails et options du plan
        </Button>
      </div>
      {execution.description && (
        <p className="whitespace-pre-wrap text-sm">{execution.description}</p>
      )}
      <p className="text-sm text-[#45564A]">
        Assignés :{' '}
        {execution.assignees_by_pole
          .flatMap((p) => p.assignees.map((a) => a.display_name))
          .join(', ') || 'À définir'}
      </p>
      {!execution.task_executions.length && (
        <p className="text-sm">Ce travail se réalise sans sous-tâche.</p>
      )}
      <ul className="space-y-3">
        {execution.task_executions.map((task) => {
          const prerequisite = execution.task_executions.find(
            (t) => t.id === task.depends_on_id,
          )
          const blocked = !!prerequisite && prerequisite.status !== 'done'
          return (
            <li
              key={task.id}
              className="rounded-xl border border-[#DADFD8] bg-white p-3"
            >
              <label className="flex items-start gap-3 text-sm font-medium">
                <input
                  type="checkbox"
                  className="mt-1 size-4"
                  checked={task.status === 'done'}
                  disabled={
                    taskMutation.isPending ||
                    blocked ||
                    (task.status === 'done'
                      ? !task.permission_hints.can_unmark_done
                      : !task.permission_hints.can_mark_done)
                  }
                  onChange={(e) =>
                    taskMutation.mutate({ id: task.id, done: e.target.checked })
                  }
                />
                <span>{task.task}</span>
              </label>
              <p className="ml-7 mt-1 text-xs text-[#45564A]">
                {task.assigned_display_name ?? 'Équipe'}
                {task.deadline_at
                  ? ` · ${new Date(task.deadline_at).toLocaleDateString('fr-FR')}`
                  : ''}
              </p>
              {blocked && (
                <p className="mt-2 text-xs text-[#754500]">
                  En attente de « {prerequisite.task} ».
                </p>
              )}
              {execution.permission_hints.can_update &&
                task.status === 'pending' &&
                execution.task_executions.length > 1 && (
                  <label className="mt-3 grid gap-1 text-xs">
                    À faire après
                    <select
                      className={`${inputClass} py-2`}
                      disabled={dependency.isPending}
                      value={task.depends_on_id ?? ''}
                      onChange={(e) =>
                        dependency.mutate({
                          taskId: task.id,
                          prerequisite: e.target.value || null,
                        })
                      }
                    >
                      <option value="">Aucune dépendance</option>
                      {execution.task_executions
                        .filter((t) => t.id !== task.id)
                        .map((t) => (
                          <option key={t.id} value={t.id}>
                            {t.task}
                          </option>
                        ))}
                    </select>
                  </label>
                )}
            </li>
          )
        })}
      </ul>
      <ErrorNote
        error={
          taskMutation.error ??
          dependency.error ??
          doneMutation.error ??
          validation.error
        }
      />
      <div className="flex flex-wrap gap-2">
        {execution.permission_hints.can_mark_done && (
          <Button
            disabled={doneMutation.isPending}
            onClick={() => doneMutation.mutate()}
          >
            Travail terminé
          </Button>
        )}
        {execution.permission_hints.can_validate && (
          <Button onClick={() => setValidating(true)}>
            Valider la réalisation
          </Button>
        )}
      </div>
      <details>
        <summary className="cursor-pointer py-2 font-semibold">
          Discussion de ce travail
        </summary>
        <CommentSection
          establishmentId={site}
          targetType="action-plan-execution"
          targetId={executionId}
          attachEnabled
          documentFlow
          pinComposer={false}
        />
      </details>
      <ActionPlanExecutionValidateRatingSheet
        open={validating}
        stars={stars}
        comment={comment}
        isPending={validation.isPending}
        onStarsChange={setStars}
        onCommentChange={setComment}
        onConfirm={() => {
          if (stars !== null) validation.mutate()
        }}
        onClose={() => setValidating(false)}
      />
    </div>
  )
}
