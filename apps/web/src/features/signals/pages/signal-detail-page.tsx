import { LoaderCircle } from 'lucide-react'

import { useAuth } from '@/app/auth-provider'
import { TerrainCard, TerrainErrorState, TerrainFieldLabel } from '@/components/ui/terrain'
import { resolveApiErrorMessage } from '@/lib/error-message'
import { CommentSection } from '@/features/comments/components/comment-section'
import { cn } from '@/lib/utils'

import { SignalDetailPhotoSection } from '../components/signal-detail-photo-section'
import { SignalDetailStickyFooter } from '../components/signal-detail-sticky-footer'
import { SignalPinUrgencyActions } from '../components/signal-pin-urgency-actions'
import { SignalStatusBadge } from '../components/signal-status-badge'
import { SignalDetailClassificationSection } from '../components/signal-detail-classification-section'
import { SignalUrgencyBadge } from '../components/signal-urgency-badge'
import {
  useCancelSignalMutation,
  usePinSignalMutation,
  useResolveSignalMutation,
  useSignalDetailQuery,
  useSignalUrgencyMutation,
  useUnpinSignalMutation,
} from '../hooks'
import { SignalsApiError } from '../api'
import { shouldShowSignalCreateActionPlan } from '../lib/signal-create-action'
import { formatSignalRelativeTime, formatSignalAggregationLabel } from '../lib/signal-display'

type SignalDetailPageProps = {
  signalId: string
  onNavigate: (pathname: string) => void
}

function formatDescriptionContent(structuredSummary: string): string {
  const trimmed = structuredSummary.trim()
  return trimmed.length > 0 ? trimmed : 'Description indisponible.'
}

export function SignalDetailPage({ signalId, onNavigate }: SignalDetailPageProps) {
  const auth = useAuth()
  const establishmentId = auth.bootstrap?.active_membership?.establishment_id ?? null

  const lifecycleClosed = () => {
    onNavigate('/signals')
  }

  const detailQuery = useSignalDetailQuery(establishmentId, signalId)
  const pinMutation = usePinSignalMutation(establishmentId, signalId)
  const unpinMutation = useUnpinSignalMutation(establishmentId, signalId)
  const urgencyMutation = useSignalUrgencyMutation(establishmentId, signalId)
  const cancelMutation = useCancelSignalMutation(establishmentId, signalId, {
    onClosed: lifecycleClosed,
  })
  const resolveMutation = useResolveSignalMutation(establishmentId, signalId)

  const lifecycleError =
    cancelMutation.error ?? resolveMutation.error ?? null

  const isPending =
    pinMutation.isPending ||
    unpinMutation.isPending ||
    urgencyMutation.isPending ||
    cancelMutation.isPending ||
    resolveMutation.isPending

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
        message={resolveApiErrorMessage(detailQuery.error, SignalsApiError, 'Une erreur est survenue.')}
        onRetry={() => void detailQuery.refetch()}
      />
    )
  }

  const signal = detailQuery.data
  const reporterName = signal.source_context.reporter_display_name?.trim()
  const showStickyCreateActionFooter = shouldShowSignalCreateActionPlan(signal.permission_hints)
  const hasLifecycleSticky =
    signal.permission_hints.can_resolve || signal.permission_hints.can_cancel
  const showStickyFooter = hasLifecycleSticky || showStickyCreateActionFooter

  return (
    <div className="flex min-h-full flex-col">
      <div
        className={cn(
          'flex flex-1 flex-col gap-2.5 px-3 pt-2',
          showStickyFooter ? 'pb-40' : 'pb-4',
        )}
      >
        <TerrainCard>
          <h2 className="text-[17px] font-semibold leading-snug text-[#1a1a1a]">{signal.title}</h2>
          <div className="mt-2 flex flex-wrap gap-1.5">
            <SignalUrgencyBadge urgency={signal.urgency} />
            <SignalStatusBadge status={signal.status} variant="detail" />
          </div>
          <p className="mt-2 text-[11px] text-[#aaa]">
            il y a {formatSignalRelativeTime(signal.last_activity_at)}
          </p>
          {(reporterName || signal.aggregation_count > 0) ? (
            <div className="mt-1 flex items-center justify-between gap-2 text-[11px] text-[#aaa]">
              <span className="min-w-0 truncate">
                {reporterName ? `Signalé par ${reporterName}` : '\u00a0'}
              </span>
              {signal.aggregation_count > 0 ? (
                <span className="shrink-0">
                  {formatSignalAggregationLabel(signal.aggregation_count)}
                </span>
              ) : null}
            </div>
          ) : null}
        </TerrainCard>

        <SignalDetailClassificationSection signal={signal} />

        <TerrainCard>
          <TerrainFieldLabel>Description</TerrainFieldLabel>
          <p className="mt-2 text-[13px] leading-relaxed text-[#444]">
            {formatDescriptionContent(signal.structured_summary)}
          </p>
        </TerrainCard>

        <SignalPinUrgencyActions
          hints={signal.permission_hints}
          isPinned={signal.is_pinned}
          urgency={signal.urgency}
          isPending={isPending}
          onPin={() => void pinMutation.mutate()}
          onUnpin={() => void unpinMutation.mutate()}
          onSetUrgency={(urgency) => void urgencyMutation.mutate(urgency)}
        />

        <SignalDetailPhotoSection mediaItems={signal.media_items ?? []} />

        {establishmentId ? (
          <CommentSection
            establishmentId={establishmentId}
            targetType="signal"
            targetId={signalId}
          />
        ) : null}
      </div>

      {showStickyFooter ? (
        <SignalDetailStickyFooter
          hints={signal.permission_hints}
          isPending={isPending}
          showCreateActionPlan={showStickyCreateActionFooter}
          onResolve={() => void resolveMutation.mutate()}
          onCancel={() => void cancelMutation.mutate()}
          onCreateActionPlan={() => onNavigate(`/signals/${signalId}/plan`)}
          lifecycleErrorMessage={
            lifecycleError ? resolveApiErrorMessage(lifecycleError, SignalsApiError, 'Une erreur est survenue.') : null
          }
        />
      ) : null}
    </div>
  )
}
