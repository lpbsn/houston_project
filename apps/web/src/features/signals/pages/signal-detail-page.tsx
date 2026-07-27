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
import { useSignalDetailQuery } from '../hooks'
import { SignalsApiError } from '../api'
import { shouldShowSignalCreateActionPlan } from '../lib/signal-create-action'
import { formatSignalRelativeTime, formatSignalAggregationLabel } from '../lib/signal-display'

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
  const highlightCommentId = initialDeepLink.commentId

  const detailQuery = useSignalDetailQuery(establishmentId, signalId)

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
  const showStickyFooter = activeTab === 'details' && showStickyCreateActionFooter

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

          <SignalDetailClassificationSection signal={signal} />

          <TerrainCard>
            <SignalDetailLabel>Description</SignalDetailLabel>
            <p className="mt-2 text-[13px] leading-relaxed text-[#1a1a1a]">
              {formatDescriptionContent(signal.structured_summary)}
            </p>
          </TerrainCard>

          <SignalDetailPhotoSection mediaItems={signal.media_items ?? []} />

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
    </div>
  )
}
