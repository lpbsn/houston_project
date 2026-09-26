import { ArrowLeft, LoaderCircle } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'

import { serializeScopedExecutionDetailPath } from '@/app/scoped-terrain'
import { useAuth } from '@/app/auth-provider'
import { Button } from '@/components/ui/button'
import { TerrainCard, TerrainErrorState } from '@/components/ui/terrain'
import { isDesktopWebLanding } from '@/features/auth/lib/authenticated-landing'
import { parseDetailDeepLink } from '@/features/comments/lib/detail-deep-link'
import {
  buildAnalyticsSignalActionCreatePath,
  type AnalyticsSignalReturnContext,
} from '@/features/analytics/lib/analytics-url-state'
import { resolveApiErrorMessage } from '@/lib/error-message'
import { useLgViewport } from '@/lib/lg-viewport'
import { useLocationSearch } from '@/lib/location-search'
import { terrainBackButtonClassName } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'
import { CommentSection } from '@/features/comments/components/comment-section'

import { SignalDetailMainBlock } from '../components/signal-detail-main-block'
import { SignalDetailPhotoSection } from '../components/signal-detail-photo-section'
import { SignalDetailStickyFooter } from '../components/signal-detail-sticky-footer'
import {
  SignalDetailTabs,
  type SignalDetailTab,
} from '../components/signal-detail-tabs'
import { SignalLinkedActionPlansSection } from '../components/signal-linked-action-plans-section'
import { SignalDetailClassificationSection } from '../components/signal-detail-classification-section'
import { SignalDetailLabel } from '../components/signal-detail-label'
import { SignalDetailLocationSection } from '../components/signal-detail-location-section'
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
import { formatSignalRelativeTime, formatSignalSimilarObservationsLabel } from '../lib/signal-display'

type SignalDetailPageProps = {
  signalId: string
  onNavigate: (pathname: string, options?: { replace?: boolean }) => void
  onBack?: () => void
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
  onBack,
  analyticsSignalReturnContext = null,
  establishmentId: establishmentIdProp,
  source = 'establishment',
}: SignalDetailPageProps) {
  const auth = useAuth()
  const isDesktopWeb = isDesktopWebLanding(useLgViewport())
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
  const commentsAnchorRef = useRef<HTMLElement>(null)
  const shouldScrollToComments =
    isDesktopWeb && (initialDeepLink.tab === 'comments' || initialDeepLink.commentId != null)

  const detailReady = !detailQuery.isLoading && !detailQuery.isError && detailQuery.data != null

  useEffect(() => {
    if (!shouldScrollToComments || !detailReady) {
      return
    }
    commentsAnchorRef.current?.scrollIntoView({ block: 'start' })
  }, [shouldScrollToComments, detailReady])

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
  const reporterName = signal.source_context.reporter_display_name?.trim() || null
  const description = formatDescriptionContent(signal.structured_summary)
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

  const classificationSection = (
    <SignalDetailClassificationSection
      signal={signal}
      canQualify={canQualifyRouting}
      isQualifyOpening={qualifySheet.opening}
      qualifyErrorMessage={!qualifySheet.open ? qualifySheet.errorMessage : null}
      onQualify={() => void qualifySheet.openForSignal(signal.id)}
      context={
        isDesktopWeb
          ? {
              status: signal.status,
              relativeTimeLabel: `il y a ${formatSignalRelativeTime(signal.last_activity_at)}`,
              reporterName,
              aggregationLabel:
                signal.aggregation_count > 0
                  ? formatSignalSimilarObservationsLabel(signal.aggregation_count)
                  : null,
            }
          : undefined
      }
    />
  )
  const linkedPlans = (
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
  )
  const resolutionSection = (
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
  )
  const showPageCreateAction = (isDesktopWeb || activeTab === 'details') && showCreateActionPlan
  const detailsVisible = isDesktopWeb || activeTab === 'details'

  return (
    <div className="flex h-full min-h-0 flex-col" data-testid="signal-detail-root">
      <div
        data-testid="signal-detail-frame"
        className="flex h-full min-h-0 w-full flex-1 flex-col"
      >
      {isDesktopWeb && (onBack || showPageCreateAction) ? (
        <header
          data-testid="signal-detail-desktop-header"
          className="shrink-0 border-b border-[#E8E6DF] bg-white px-6 py-3"
        >
          <div className="mx-auto flex w-full max-w-6xl items-center justify-between gap-3">
          {onBack ? (
            <Button
              type="button"
              variant="ghost"
              className={terrainBackButtonClassName()}
              onClick={onBack}
            >
              <ArrowLeft className="mr-1 h-4 w-4" aria-hidden />
              Retour
            </Button>
          ) : (
            <span />
          )}
          {showPageCreateAction ? (
            <Button
              type="button"
              className="h-9 shrink-0 rounded-lg px-3 text-sm font-semibold"
              onClick={() => onNavigate(createActionPlanPath)}
            >
              Créer un plan
            </Button>
          ) : null}
          </div>
        </header>
      ) : null}
      {isDesktopWeb ? null : (
      <div
        data-testid="signal-detail-tab-bar"
        className="shrink-0 bg-[#F5F4F0] px-3 pt-1.5 pb-1"
      >
        <SignalDetailTabs
          activeTab={activeTab}
          onChange={handleTabChange}
        />
      </div>
      )}

      <div
        className={cn(
          'flex min-h-0 flex-1 flex-col',
          isDesktopWeb && 'mx-auto w-full max-w-6xl overflow-y-auto overscroll-y-contain px-6 pt-4 pb-8',
        )}
      >
        <div
          role={isDesktopWeb ? undefined : 'tabpanel'}
          id="signal-detail-panel-details"
          aria-labelledby={isDesktopWeb ? undefined : 'signal-detail-tab-details'}
          data-testid="signal-detail-details-panel"
          className={
            detailsVisible
              ? isDesktopWeb
                ? 'grid grid-cols-1 items-start gap-4 xl:grid-cols-[minmax(0,1fr)_18rem] xl:items-stretch'
                : 'flex min-h-0 flex-1 flex-col'
              : 'hidden'
          }
        >
          {isDesktopWeb ? (
            <>
              <div data-testid="signal-detail-main" className="flex min-w-0 flex-col gap-4 xl:h-full">
                <TerrainCard>
                  <SignalDetailLabel>Titre</SignalDetailLabel>
                  <h1 className="mt-2 text-[13px] font-normal leading-relaxed text-[#1a1a1a]">
                    {signal.title}
                  </h1>
                </TerrainCard>
                <TerrainCard>
                  <SignalDetailLabel>Description</SignalDetailLabel>
                  <p className="mt-2 text-[13px] leading-relaxed text-[#1a1a1a]">{description}</p>
                </TerrainCard>
                <SignalDetailPhotoSection
                  mediaItems={signal.media_items ?? []}
                  tileSize="comfortable"
                />
                {resolutionSection}
                {linkedPlans}
                {signal.establishment_id ?? establishmentId ? (
                  <section
                    ref={commentsAnchorRef}
                    id="signal-detail-comments"
                    aria-label="Commentaires"
                    data-testid="signal-detail-comments-section"
                    className="flex scroll-mt-4 flex-col xl:min-h-0 xl:flex-1"
                  >
                    <TerrainCard className="flex flex-1 flex-col">
                      <SignalDetailLabel>Commentaires</SignalDetailLabel>
                      <CommentSection
                        establishmentId={signal.establishment_id ?? establishmentId ?? ''}
                        targetType="signal"
                        targetId={signalId}
                        highlightCommentId={highlightCommentId}
                        readOnly={source === 'cross'}
                        documentFlow
                      />
                    </TerrainCard>
                  </section>
                ) : null}
              </div>
              <div
                data-testid="signal-detail-context"
                className="flex min-w-0 flex-col gap-4 self-start xl:col-start-2 xl:row-start-1"
              >
                {classificationSection}
                <SignalDetailLocationSection locationText={signal.location_text} />
              </div>
            </>
          ) : (
            <>
              <div
                data-testid="signal-detail-details-content"
                className="min-h-0 flex-1 overflow-y-auto overscroll-y-contain px-3 pt-2 pb-4"
              >
                <div className="flex flex-col gap-2.5">
                  <SignalDetailMainBlock
                    signal={signal}
                    reporterName={reporterName}
                    description={description}
                  />
                  {classificationSection}
                  {resolutionSection}
                  {linkedPlans}
                </div>
              </div>
              {showPageCreateAction ? (
                <SignalDetailStickyFooter
                  onCreateActionPlan={() => onNavigate(createActionPlanPath)}
                />
              ) : null}
            </>
          )}
        </div>

        {!isDesktopWeb && hasOpenedComments && (signal.establishment_id ?? establishmentId) ? (
          <div
            role="tabpanel"
            id="signal-detail-panel-comments"
            aria-labelledby="signal-detail-tab-comments"
            data-testid="signal-detail-comments-panel"
            className={
              activeTab === 'comments'
                ? // Match execution detail: CommentSection owns list scroll + pinned composer.
                  'flex min-h-0 flex-1 flex-col px-3 pt-2 pb-4'
                : 'hidden'
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
