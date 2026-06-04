import { LoaderCircle } from 'lucide-react'

import { useAuth } from '@/app/auth-provider'
import { TerrainCard, TerrainErrorState, TerrainFieldLabel } from '@/components/ui/terrain'
import { ActionDetailCommentsDisabledSection } from '@/features/actions/components/action-detail-disabled-section'
import { cn } from '@/lib/utils'

import { SignalDetailPhotoSection } from '../components/signal-detail-photo-section'
import { SignalDetailStickyFooter } from '../components/signal-detail-sticky-footer'
import { SignalPinUrgencyActions } from '../components/signal-pin-urgency-actions'
import { SignalStatusBadge } from '../components/signal-status-badge'
import { SignalTaxonomyBadges } from '../components/signal-taxonomy-badges'
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
import { formatSignalRelativeTime } from '../lib/signal-display'
import type { SignalDetail } from '../types'

type SignalDetailPageProps = {
  signalId: string
  onNavigate: (pathname: string) => void
}

function getErrorMessage(error: unknown): string {
  if (error instanceof SignalsApiError) {
    return error.detail
  }
  if (error instanceof Error) {
    return error.message
  }
  return 'Une erreur est survenue.'
}

function formatDescriptionContent(structuredSummary: string): string {
  const trimmed = structuredSummary.trim()
  return trimmed.length > 0 ? trimmed : 'Description indisponible.'
}

function resolveMediaCount(signal: SignalDetail): number {
  if (signal.media_count > 0) {
    return signal.media_count
  }
  return signal.source_context.media_count ?? 0
}

export function SignalDetailPage({ signalId, onNavigate }: SignalDetailPageProps) {
  const auth = useAuth()
  const establishmentId = auth.bootstrap?.active_membership?.establishment_id ?? null
  const role = auth.bootstrap?.active_membership?.role
  const canCreateAction =
    role === 'owner' || role === 'director' || role === 'manager'

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
        message={getErrorMessage(detailQuery.error)}
        onRetry={() => void detailQuery.refetch()}
      />
    )
  }

  const signal = detailQuery.data
  const reporterName = signal.source_context.reporter_display_name?.trim()
  const mediaCount = resolveMediaCount(signal)
  const showCreateActionPlan =
    canCreateAction && (signal.status === 'open' || signal.status === 'in_progress')
  const showStickyCreateActionFooter = showCreateActionPlan
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
            <SignalTaxonomyBadges
              moduleKey={signal.module_key}
              domainKey={signal.domain_key}
              subjectKey={signal.subject_key}
            />
            <SignalStatusBadge status={signal.status} variant="detail" />
          </div>
          <p className="mt-2 text-[11px] text-[#aaa]">
            {signal.location_text ? `📍 ${signal.location_text} · ` : ''}
            il y a {formatSignalRelativeTime(signal.last_activity_at)}
          </p>
          {reporterName ? (
            <p className="mt-1 text-[11px] text-[#aaa]">Signalé par {reporterName}</p>
          ) : null}
        </TerrainCard>

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

        <SignalDetailPhotoSection mediaCount={mediaCount} />

        <ActionDetailCommentsDisabledSection description="Les échanges autour de ce signal seront disponibles bientôt." />
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
            lifecycleError ? getErrorMessage(lifecycleError) : null
          }
        />
      ) : null}
    </div>
  )
}
