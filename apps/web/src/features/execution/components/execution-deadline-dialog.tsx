import { useState } from 'react'
import { TerrainDialog, TerrainErrorState } from '@/components/ui/terrain'
import { Button } from '@/components/ui/button'
import {
  useActionPlanExecutionDetailQuery,
  useUpdateActionPlanExecutionMutation,
} from '@/features/action-plans/hooks'
import { executionDeadlineChange } from '@/features/action-plans/lib/execution-deadline-change'
import { resolveActionPlanErrorMessage } from '@/features/action-plans/lib/action-plan-errors'
import { notifySuccess } from '@/lib/success-toast'

export function ExecutionDeadlineDialog({
  establishmentId,
  executionId,
  date,
  timeZone,
  onClose,
  onOpenExecution,
}: {
  establishmentId: string
  executionId: string
  date: string
  timeZone: string
  onClose: () => void
  onOpenExecution: (id: string) => void
}) {
  const detail = useActionPlanExecutionDetailQuery(establishmentId, executionId)
  const mutation = useUpdateActionPlanExecutionMutation(establishmentId, executionId)
  const [error, setError] = useState<string | null>(null)
  let request: ReturnType<typeof executionDeadlineChange> | null = null
  let restriction: string | null = null
  if (detail.data) {
    try {
      request = executionDeadlineChange(detail.data, date, timeZone)
    } catch (cause) {
      restriction = cause instanceof Error ? cause.message : 'Échéance invalide.'
    }
  }
  return (
    <TerrainDialog
      open
      title="Changer l’échéance"
      onClose={onClose}
      dismissible={!mutation.isPending}
    >
      {detail.isLoading && <p role="status">Chargement du plan…</p>}
      {detail.isError && (
        <TerrainErrorState
          message="Le plan n’a pas pu être chargé."
          onRetry={() => void detail.refetch()}
        />
      )}
      {detail.data && (
        <div className="space-y-4">
          <p className="font-semibold text-[#1a1a1a]">{detail.data.title}</p>
          <p>
            Nouvelle échéance : <strong>{date.split('-').reverse().join('/')}</strong>. Le début du
            plan reste inchangé.
          </p>
          {restriction && <p role="alert">{restriction}</p>}
          {error && (
            <p role="alert" className="text-destructive">
              {error}
            </p>
          )}
          <div className="flex flex-wrap gap-2">
            <Button
              disabled={!request || mutation.isPending || detail.isFetching || Boolean(error)}
              onClick={async () => {
                if (!request) return
                try {
                  await mutation.mutateAsync(request)
                  notifySuccess({ message: 'Échéance mise à jour.', kind: 'updated' })
                  onClose()
                } catch (cause) {
                  setError(
                    resolveActionPlanErrorMessage(
                      cause,
                      'Le plan a peut-être changé. Rechargez-le avant de confirmer.',
                    ),
                  )
                }
              }}
            >
              Confirmer
            </Button>
            {error && (
              <Button
                variant="outline"
                disabled={detail.isFetching}
                onClick={async () => {
                  const fresh = await detail.refetch()
                  if (fresh.isSuccess) setError(null)
                }}
              >
                Recharger
              </Button>
            )}
            <Button
              variant="outline"
              disabled={mutation.isPending}
              onClick={() => {
                onClose()
                onOpenExecution(executionId)
              }}
            >
              Ouvrir le plan
            </Button>
          </div>
        </div>
      )}
    </TerrainDialog>
  )
}
