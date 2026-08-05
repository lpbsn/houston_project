import { LoaderCircle } from 'lucide-react'
import { useState } from 'react'

import { useAuth } from '@/app/auth-provider'
import { TerrainCard, TerrainErrorState } from '@/components/ui/terrain'
import { readCurrentDetailDeepLink } from '@/features/comments/lib/detail-deep-link'
import { resolveApiErrorMessage } from '@/lib/error-message'
import { CommentSection } from '@/features/comments/components/comment-section'
import { cn } from '@/lib/utils'

import { SignalDetailPhotoSection } from '../components/signal-detail-photo-section'
import { SignalDetailStickyFooter } from '../components/signal-detail-sticky-footer'
import {
  SignalDetailTabs,
  type SignalDetailTab,
} from '../components/signal-detail-tabs'
import { SignalLinkedActionPlansSection } from '../components/signal-linked-action-plans-section'
import { SignalStatusBadge } from '../components/signal-status-badge'
import { SignalDetailClassificationSection } from '../components/signal-detail-classification-section'
import { SignalDetailLabel } from '../components/signal-detail-label'
import { SignalQualifyRoutingSheet } from '../components/signal-qualify-routing-sheet'
import {
  resolutionRequestEventsFromDetail,
  SignalResolutionRequestSection,
} from '../components/signal-resolution-request-section'
import {
  useApproveSignalResolutionRequestMutation,
  useCancelSignalResolutionRequestMutation,
  useCreateSignalResolutionRequestMutation,
  useRejectSignalResolutionRequestMutation,
  useSignalDetailQuery,
} from '../hooks'
import { useSignalQualifySheet } from '../hooks/use-signal-qualify-sheet'
import { SignalsApiError } from '../api'
import { shouldShowSignalQualifyRouting } from '../lib/signal-qualify-routing'
import { shouldShowSignalCreateActionPlan } from '../lib/signal-create-action'
import { formatSignalRelativeTime, formatSignalAggregationLabel } from '../lib/signal-display'
import { SIGNAL_IN_PROGRESS_RESOLVE_VIA_ACTION_PLAN_HINT } from '../lib/signal-feed-card-actions'

type SignalDetailPageProps = {
  signalId: string
  onNavigate: (pathname: string, options?: { replace?: boolean }) => void
}

function formatDescriptionContent(structuredSummary: string): string {
  const trimmed = structuredSummary.trim()
  return trimmed.length > 0 ? trimmed : 'Description indisponible.'
}

export function SignalDetailPage({ signalId, onNavigate }: SignalDetailPageProps) {
  const auth = useAuth()
  const establishmentId = auth.bootstrap?.active_membership?.establishment_id ?? null

  const initialDeepLink = readCurrentDetailDeepLink()
  const [activeTab, setActiveTab] = useState<SignalDetailTab>(
    initialDeepLink.tab === 'comments' ? 'comments' : 'details',
  )
  const [hasOpenedComments, setHasOpenedComments] = useState(initialDeepLink.tab === 'comments')
  const [requestActionError, setRequestActionError] = useState<string | null>(null)
  const highlightCommentId = initialDeepLink.commentId

  const detailQuery = useSignalDetailQuery(establishmentId, signalId)
  const createRequestMutation = useCreateSignalResolutionRequestMutation(establishmentId)
  const approveRequestMutation = useApproveSignalResolutionRequestMutation(establishmentId)
  const rejectRequestMutation = useRejectSignalResolutionRequestMutation(establishmentId)
  const cancelRequestMutation = useCancelSignalResolutionRequestMutation(establishmentId)
  const qualifySheet = useSignalQualifySheet({ establishmentId, onNavigate })

  const handleTabChange = (tab: SignalDetailTab) => {
    if (tab === 'comments') {
      setHasOpenedComments(true)
    }
    setActiveTab(tab)
  }

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
  const canQualifyRouting = shouldShowSignalQualifyRouting(signal.permission_hints)
  const showStickyFooter = activeTab === 'details' && showStickyCreateActionFooter
  const resolutionRequest = signal.resolution_request
  const resolutionRequestEvents = resolutionRequestEventsFromDetail(signal)

  async function handleCreateResolutionRequest() {
    setRequestActionError(null)
    try {
      await createRequestMutation.mutateAsync({ signalId })
    } catch (error) {
      setRequestActionError(resolveApiErrorMessage(error, SignalsApiError, 'Une erreur est survenue.'))
    }
  }

  async function handleApproveResolutionRequest() {
    if (!resolutionRequest) {
      return
    }
    setRequestActionError(null)
    try {
      await approveRequestMutation.mutateAsync({
        signalId,
        requestId: resolutionRequest.id,
      })
    } catch (error) {
      setRequestActionError(resolveApiErrorMessage(error, SignalsApiError, 'Une erreur est survenue.'))
    }
  }

  async function handleRejectResolutionRequest() {
    if (!resolutionRequest) {
      return
    }
    setRequestActionError(null)
    try {
      await rejectRequestMutation.mutateAsync({
        signalId,
        requestId: resolutionRequest.id,
      })
    } catch (error) {
      setRequestActionError(resolveApiErrorMessage(error, SignalsApiError, 'Une erreur est survenue.'))
    }
  }

  async function handleCancelResolutionRequest() {
    if (!resolutionRequest) {
      return
    }
    setRequestActionError(null)
    try {
      await cancelRequestMutation.mutateAsync({
        signalId,
        requestId: resolutionRequest.id,
      })
    } catch (error) {
      setRequestActionError(resolveApiErrorMessage(error, SignalsApiError, 'Une erreur est survenue.'))
    }
  }

  return (
    <div className="flex min-h-full flex-col">
      <div className="px-3 pt-2">
        <SignalDetailTabs activeTab={activeTab} onChange={handleTabChange} />
      </div>

      <div
        className={cn(
          'flex flex-1 flex-col gap-2.5 px-3 pt-2',
          showStickyFooter ? 'pb-40' : 'pb-4',
        )}
      >
        <div
          role="tabpanel"
          id="signal-detail-panel-details"
          aria-labelledby="signal-detail-tab-details"
          className={cn('flex flex-col gap-2.5', activeTab !== 'details' && 'hidden')}
        >
          <TerrainCard>
            <h2 className="text-[17px] font-semibold leading-snug text-[#1a1a1a]">{signal.title}</h2>
            <div className="mt-2 flex flex-wrap gap-1.5">
              <SignalStatusBadge status={signal.status} variant="detail" />
            </div>
            <p className="mt-2 text-[11px] text-[#aaa]">
              il y a {formatSignalRelativeTime(signal.last_activity_at)}
            </p>
            {(reporterName || signal.aggregation_count > 0) ? (
              <div className="mt-3 flex items-center justify-between gap-2 text-[11px] text-[#aaa]">
                <span className="min-w-0 truncate">
                  {reporterName ? `Rapportée par ${reporterName}` : '\u00a0'}
                </span>
                {signal.aggregation_count > 0 ? (
                  <span className="shrink-0">
                    {formatSignalAggregationLabel(signal.aggregation_count)}
                  </span>
                ) : null}
              </div>
            ) : null}
          </TerrainCard>

          <SignalDetailClassificationSection
            signal={signal}
            canQualify={canQualifyRouting}
            isQualifyOpening={qualifySheet.opening}
            qualifyErrorMessage={!qualifySheet.open ? qualifySheet.errorMessage : null}
            onQualify={() => void qualifySheet.openForSignal(signal.id)}
          />

          <TerrainCard>
            <SignalDetailLabel>Description</SignalDetailLabel>
            <p className="mt-2 text-[13px] leading-relaxed text-[#1a1a1a]">
              {formatDescriptionContent(signal.structured_summary)}
            </p>
          </TerrainCard>

          <SignalResolutionRequestSection
            events={resolutionRequestEvents}
            permissionHints={signal.permission_hints}
            pendingRequestId={resolutionRequest?.id ?? null}
            errorMessage={requestActionError}
            isCreatePending={createRequestMutation.isPending}
            isCancelPending={cancelRequestMutation.isPending}
            isApprovePending={approveRequestMutation.isPending}
            isRejectPending={rejectRequestMutation.isPending}
            onCreate={() => void handleCreateResolutionRequest()}
            onCancel={() => void handleCancelResolutionRequest()}
            onApprove={() => void handleApproveResolutionRequest()}
            onReject={() => void handleRejectResolutionRequest()}
          />

          <SignalDetailPhotoSection mediaItems={signal.media_items ?? []} />

          {signal.status === 'in_progress' ? (
            <TerrainCard>
              <p className="text-[13px] leading-relaxed text-[#7D7B75]">
                {SIGNAL_IN_PROGRESS_RESOLVE_VIA_ACTION_PLAN_HINT}
              </p>
            </TerrainCard>
          ) : null}

          <SignalLinkedActionPlansSection
            executions={signal.linked_action_plan_executions}
            onSelect={(executionId) => onNavigate(`/action-plans/executions/${executionId}`)}
          />
        </div>

        {hasOpenedComments && establishmentId ? (
          <div
            role="tabpanel"
            id="signal-detail-panel-comments"
            aria-labelledby="signal-detail-tab-comments"
            className={cn(activeTab !== 'comments' && 'hidden')}
          >
            <CommentSection
              establishmentId={establishmentId}
              targetType="signal"
              targetId={signalId}
              highlightCommentId={highlightCommentId}
            />
          </div>
        ) : null}
      </div>

      {showStickyFooter ? (
        <SignalDetailStickyFooter
          onCreateActionPlan={() => onNavigate(`/signals/${signalId}/plan`)}
        />
      ) : null}

      {establishmentId && qualifySheet.open && qualifySheet.signal ? (
        <SignalQualifyRoutingSheet
          key={qualifySheet.signal.id}
          open={qualifySheet.open}
          establishmentId={establishmentId}
          signal={qualifySheet.signal}
          isPending={qualifySheet.isPending}
          errorMessage={qualifySheet.errorMessage}
          onClose={qualifySheet.close}
          onSubmit={(patch) => void qualifySheet.submit(patch)}
        />
      ) : null}
    </div>
  )
}
