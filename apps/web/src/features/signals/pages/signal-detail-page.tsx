import { LoaderCircle } from 'lucide-react'
import { useState } from 'react'

import { serializeScopedExecutionDetailPath } from '@/app/scoped-terrain'
import { useAuth } from '@/app/auth-provider'
import { TerrainCard, TerrainErrorState } from '@/components/ui/terrain'
import { parseDetailDeepLink } from '@/features/comments/lib/detail-deep-link'
import {
  buildAnalyticsSignalActionCreatePath,
  type AnalyticsSignalReturnContext,
} from '@/features/analytics/lib/analytics-url-state'
import { resolveApiErrorMessage } from '@/lib/error-message'
import { useLocationSearch } from '@/lib/location-search'
import { CommentSection } from '@/features/comments/components/comment-section'

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
  analyticsSignalReturnContext?: AnalyticsSignalReturnContext | null
  establishmentId?: string | null
  source?: 'establishment' | 'cross'
}

function formatDescriptionContent(structuredSummary: string): string {
  const trimmed = structuredSummary.trim()
  return trimmed.length > 0 ? trimmed : 'Description indisponible.'
}

export function SignalDetailPage({
  signalId,
  onNavigate,
  analyticsSignalReturnContext = null,
  establishmentId: establishmentIdProp,
  source = 'establishment',
}: SignalDetailPageProps) {
  const auth = useAuth()
  const sessionEstablishmentId = auth.bootstrap?.active_membership?.establishment_id ?? null
  const establishmentId = establishmentIdProp ?? sessionEstablishmentId
  const locationSearch = useLocationSearch()
  const initialDeepLink = parseDetailDeepLink(locationSearch)
  const [activeTab, setActiveTab] = useState<SignalDetailTab>(
    initialDeepLink.tab === 'comments' ? 'comments' : 'details',
  )
  const [hasOpenedComments, setHasOpenedComments] = useState(initialDeepLink.tab === 'comments')
  const [requestActionError, setRequestActionError] = useState<string | null>(null)
  const highlightCommentId = initialDeepLink.commentId

  const detailQuery = useSignalDetailQuery(establishmentId, signalId, { source })
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
  const showCreateActionPlan = shouldShowSignalCreateActionPlan(signal.permission_hints)
  const canQualifyRouting = shouldShowSignalQualifyRouting(signal.permission_hints)
  const resolutionRequest = signal.resolution_request
  const resolutionRequestEvents = resolutionRequestEventsFromDetail(signal)
  const createActionPlanPath = analyticsSignalReturnContext
    ? buildAnalyticsSignalActionCreatePath(signalId, {
        patternId: analyticsSignalReturnContext.patternId,
        state: analyticsSignalReturnContext.state,
      })
    : `/signals/${signalId}/plan`

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
      <div
        data-testid="signal-detail-frame"
        className="flex min-h-full w-full flex-1 flex-col"
      >
      <div
        data-testid="signal-detail-tab-bar"
        className="px-3 pt-2 lg:sticky lg:top-0 lg:z-20 lg:border-b lg:border-[#E8E6DF] lg:bg-[#F5F4F0] lg:px-6 lg:py-3"
      >
        <SignalDetailTabs activeTab={activeTab} onChange={handleTabChange} />
      </div>

      <div className="flex w-full flex-1 flex-col gap-2.5 px-3 pt-2 pb-4 lg:gap-4 lg:px-6 lg:pt-4 lg:pb-6">
        <div
          role="tabpanel"
          id="signal-detail-panel-details"
          aria-labelledby="signal-detail-tab-details"
          data-testid="signal-detail-details-panel"
          className={
            activeTab === 'details'
              ? 'flex flex-col gap-2.5 lg:gap-4'
              : 'hidden'
          }
        >
          <TerrainCard className="max-lg:order-1 lg:p-5">
            <h2 className="text-[17px] font-semibold leading-snug text-[#1a1a1a] lg:text-2xl">
              {signal.title}
            </h2>
            <div className="mt-2 flex flex-wrap gap-1.5">
              <SignalStatusBadge status={signal.status} variant="detail" />
            </div>
            <p className="mt-2 text-[11px] text-[#aaa] lg:text-xs">
              il y a {formatSignalRelativeTime(signal.last_activity_at)}
            </p>
            {(reporterName || signal.aggregation_count > 0) ? (
              <div className="mt-3 flex items-center justify-between gap-2 text-[11px] text-[#aaa] lg:text-xs">
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

          <div className="max-lg:order-2 empty:hidden">
            <SignalDetailClassificationSection
              signal={signal}
              canQualify={canQualifyRouting}
              isQualifyOpening={qualifySheet.opening}
              qualifyErrorMessage={!qualifySheet.open ? qualifySheet.errorMessage : null}
              onQualify={() => void qualifySheet.openForSignal(signal.id)}
            />
          </div>

          <TerrainCard className="max-lg:order-3">
            <SignalDetailLabel>Description</SignalDetailLabel>
            <p className="mt-2 text-[13px] leading-relaxed text-[#1a1a1a]">
              {formatDescriptionContent(signal.structured_summary)}
            </p>
          </TerrainCard>

          {signal.status === 'in_progress' ? (
            <TerrainCard className="max-lg:order-6">
              <p className="text-[13px] leading-relaxed text-[#7D7B75]">
                {SIGNAL_IN_PROGRESS_RESOLVE_VIA_ACTION_PLAN_HINT}
              </p>
            </TerrainCard>
          ) : null}

          <div className="max-lg:order-5 empty:hidden">
            <SignalDetailPhotoSection mediaItems={signal.media_items ?? []} />
          </div>

          <div className="max-lg:order-7 empty:hidden">
            <SignalLinkedActionPlansSection
              executions={signal.linked_action_plan_executions}
              onSelect={(executionId) =>
                onNavigate(
                  source === 'cross'
                    ? serializeScopedExecutionDetailPath({ type: 'cross' }, executionId)
                    : `/action-plans/executions/${executionId}`,
                )
              }
            />
          </div>

          {activeTab === 'details' && showCreateActionPlan ? (
            <SignalDetailStickyFooter
              className="max-lg:order-8 lg:relative lg:bottom-auto lg:mt-0 lg:rounded-2xl lg:border lg:border-[#E8E6DF] lg:bg-white lg:p-4 lg:shadow-none"
              onCreateActionPlan={() => onNavigate(createActionPlanPath)}
            />
          ) : null}

          <div className="max-lg:order-4 empty:hidden">
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
          </div>
        </div>

        {hasOpenedComments && (signal.establishment_id ?? establishmentId) ? (
          <div
            role="tabpanel"
            id="signal-detail-panel-comments"
            aria-labelledby="signal-detail-tab-comments"
            data-testid="signal-detail-comments-panel"
            className={
              activeTab === 'comments' ? 'flex min-h-0 flex-1 flex-col' : 'hidden'
            }
          >
            <CommentSection
              establishmentId={signal.establishment_id ?? establishmentId ?? ''}
              targetType="signal"
              targetId={signalId}
              highlightCommentId={highlightCommentId}
              readOnly={source === 'cross'}
            />
          </div>
        ) : null}
      </div>
      </div>

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
