import { LoaderCircle } from 'lucide-react'

import { useAuth } from '@/app/auth-provider'
import { TerrainErrorState } from '@/components/ui/terrain'
import { resolveApiErrorMessage } from '@/lib/error-message'
import { cn } from '@/lib/utils'

import { ActionsApiError } from '../api'
import { CommentSection } from '@/features/comments/components/comment-section'
import { ActionDetailDeadlineCard } from '../components/action-detail-deadline-card'
import { ActionDetailInstructionCard } from '../components/action-detail-instruction-card'
import { ActionDetailStickyFooter } from '../components/action-detail-sticky-footer'
import { ActionDetailSummaryCard } from '../components/action-detail-summary-card'
import { ActionLinkedSignalCard } from '../components/action-linked-signal-card'
import { ActionLinkedSignalStrip } from '../components/action-linked-signal-strip'
import { getActionLocationText } from '../lib/action-display'
import {
  useAcceptActionMutation,
  useActionDetailQuery,
  useCancelActionMutation,
  useMarkActionDoneMutation,
  useReopenActionMutation,
  useValidateActionMutation,
} from '../hooks'

type ActionDetailPageProps = {
  actionId: string
  onNavigate: (pathname: string) => void
}

export function ActionDetailPage({ actionId, onNavigate }: ActionDetailPageProps) {
  const auth = useAuth()
  const establishmentId = auth.bootstrap?.active_membership?.establishment_id ?? null

  const detailQuery = useActionDetailQuery(establishmentId, actionId)
  const acceptMutation = useAcceptActionMutation(establishmentId, actionId)
  const markDoneMutation = useMarkActionDoneMutation(establishmentId, actionId)
  const validateMutation = useValidateActionMutation(establishmentId, actionId)
  const reopenMutation = useReopenActionMutation(establishmentId, actionId)
  const cancelMutation = useCancelActionMutation(establishmentId, actionId)

  const isPending =
    acceptMutation.isPending ||
    markDoneMutation.isPending ||
    validateMutation.isPending ||
    reopenMutation.isPending ||
    cancelMutation.isPending

  const mutationError =
    acceptMutation.error ??
    markDoneMutation.error ??
    validateMutation.error ??
    reopenMutation.error ??
    cancelMutation.error ??
    null

  if (detailQuery.isLoading) {
    return (
      <div className="flex items-center justify-center py-16 text-[#7D7B75]">
        <LoaderCircle className="h-6 w-6 animate-spin" />
      </div>
    )
  }

  if (detailQuery.isError || !detailQuery.data) {
    return (
      <TerrainErrorState
        className="mx-3 mt-3"
        message={resolveApiErrorMessage(detailQuery.error, ActionsApiError, 'Une erreur est survenue.')}
        onRetry={() => void detailQuery.refetch()}
      />
    )
  }

  const action = detailQuery.data
  const hints = action.permission_hints

  const signalSummary = action.signal_summary
  const showStickyFooter = true

  return (
    <div className="flex min-h-full flex-col">
      {signalSummary ? (
        <ActionLinkedSignalStrip>
          <ActionLinkedSignalCard
            title={signalSummary.title}
            locationText={getActionLocationText(signalSummary)}
            onPress={() => onNavigate(`/signals/${signalSummary.id}`)}
          />
        </ActionLinkedSignalStrip>
      ) : null}

      <div
        className={cn(
          'flex flex-1 flex-col gap-2.5 px-3 pt-2',
          showStickyFooter ? 'pb-40' : 'pb-4',
        )}
      >
        <ActionDetailSummaryCard action={action} />

        <ActionDetailInstructionCard instruction={action.instruction} />

        <ActionDetailDeadlineCard action={action} />

        {establishmentId ? (
          <CommentSection
            establishmentId={establishmentId}
            targetType="action"
            targetId={actionId}
          />
        ) : null}
      </div>

      {showStickyFooter ? (
        <ActionDetailStickyFooter
          hints={hints}
          isPending={isPending}
          mutationErrorMessage={mutationError ? resolveApiErrorMessage(mutationError, ActionsApiError, 'Une erreur est survenue.') : null}
          onAccept={() => void acceptMutation.mutate()}
          onMarkDone={() => void markDoneMutation.mutate()}
          onValidate={() => void validateMutation.mutate()}
          onReopen={() => void reopenMutation.mutate()}
          onCancel={() => void cancelMutation.mutate()}
        />
      ) : null}
    </div>
  )
}
