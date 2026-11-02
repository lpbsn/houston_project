import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { TerrainDialog, TerrainErrorState } from '@/components/ui/terrain'
import {
  useActionPlanExecutionDetailQuery,
  useMarkActionPlanExecutionDoneMutation,
  useValidateActionPlanExecutionMutation,
  useReopenActionPlanExecutionMutation,
  useCancelActionPlanExecutionMutation,
} from '@/features/action-plans/hooks'
import { resolveActionPlanErrorMessage } from '@/features/action-plans/lib/action-plan-errors'
import { ActionPlanExecutionValidateRatingSheet } from '@/features/action-plans/components/action-plan-execution-validate-rating-sheet'
import { resolveBoardCommand, type BoardTarget } from '../lib/execution-board-transition'

export function ExecutionBoardTransitionDialog({
  establishmentId,
  executionId,
  target,
  onClose,
  onOpenExecution,
}: {
  establishmentId: string
  executionId: string
  target: BoardTarget
  onClose: () => void
  onOpenExecution: (id: string) => void
}) {
  const detail = useActionPlanExecutionDetailQuery(establishmentId, executionId)
  const done = useMarkActionPlanExecutionDoneMutation(establishmentId, executionId)
  const validate = useValidateActionPlanExecutionMutation(establishmentId, executionId)
  const reopen = useReopenActionPlanExecutionMutation(establishmentId, executionId)
  const cancel = useCancelActionPlanExecutionMutation(establishmentId, executionId)
  const [stars, setStars] = useState<number | null>(null)
  const [comment, setComment] = useState('')
  const [ratingOpen, setRatingOpen] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const pending = done.isPending || validate.isPending || reopen.isPending || cancel.isPending
  const command = detail.data ? resolveBoardCommand(detail.data, target) : null
  async function confirm() {
    if (!command || detail.isFetching || pending) return
    if (command === 'validate' && stars == null) {
      setRatingOpen(true)
      return
    }
    try {
      if (command === 'markDone') await done.mutateAsync()
      else if (command === 'reopen') await reopen.mutateAsync()
      else if (command === 'cancel') await cancel.mutateAsync()
      else if (stars != null) await validate.mutateAsync({ stars, comment })
      onClose()
    } catch (cause) {
      setRatingOpen(false)
      setError(resolveActionPlanErrorMessage(cause, 'Le plan n’a pas pu être modifié.'))
      await detail.refetch()
    }
  }
  return (
    <>
      <TerrainDialog
        open={!ratingOpen}
        title="Changer l’état du plan"
        onClose={onClose}
        dismissible={!pending}
      >
        {detail.isLoading && <p role="status">Vérification du plan…</p>}
        {detail.isError && (
          <TerrainErrorState
            message="Impossible de vérifier le plan."
            onRetry={() => void detail.refetch()}
          />
        )}
        {detail.data && (
          <div className="space-y-3">
            <p className="font-semibold">{detail.data.title}</p>
            <p>
              {command === 'markDone'
                ? detail.data.requires_validation
                  ? 'Le plan sera envoyé en validation.'
                  : 'Le plan sera marqué terminé.'
                : command === 'validate'
                  ? 'Validez la réalisation du plan en donnant une note.'
                  : command === 'reopen'
                    ? 'Le plan sera rouvert.'
                    : command === 'cancel'
                      ? 'Le plan sera annulé.'
                      : 'Ce déplacement n’est pas autorisé dans l’état actuel du plan. Consultez ses tâches et ses actions disponibles.'}
            </p>
            {error && (
              <p role="alert" className="text-destructive">
                {error}
              </p>
            )}
            <div className="flex gap-2">
              <Button
                disabled={!command || pending || detail.isFetching}
                onClick={() => void confirm()}
              >
                Confirmer
              </Button>
              <Button
                variant="outline"
                disabled={pending}
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
      <ActionPlanExecutionValidateRatingSheet
        open={ratingOpen}
        stars={stars}
        comment={comment}
        isPending={pending}
        onStarsChange={setStars}
        onCommentChange={setComment}
        onConfirm={() => void confirm()}
        onClose={() => {
          if (!pending) setRatingOpen(false)
        }}
      />
    </>
  )
}
