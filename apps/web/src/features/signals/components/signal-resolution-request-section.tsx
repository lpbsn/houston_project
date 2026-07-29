import { TerrainFeedback } from '@/components/domain/terrain-feedback'
import { Button } from '@/components/ui/button'
import { TerrainCard } from '@/components/ui/terrain'
import { cn } from '@/lib/utils'

import { SignalDetailLabel } from './signal-detail-label'
import {
  formatResolutionRequestHistoryLine,
  type ResolutionRequestHistoryEvent,
} from '../lib/signal-resolution-request-history'
import type { PermissionHints, SignalDetail } from '../types'

type SignalResolutionRequestSectionProps = {
  events: ResolutionRequestHistoryEvent[]
  permissionHints: PermissionHints
  pendingRequestId: string | null
  errorMessage: string | null
  isCreatePending: boolean
  isCancelPending: boolean
  isApprovePending: boolean
  isRejectPending: boolean
  onCreate: () => void
  onCancel: () => void
  onApprove: () => void
  onReject: () => void
}

export function SignalResolutionRequestSection({
  events,
  permissionHints,
  pendingRequestId,
  errorMessage,
  isCreatePending,
  isCancelPending,
  isApprovePending,
  isRejectPending,
  onCreate,
  onCancel,
  onApprove,
  onReject,
}: SignalResolutionRequestSectionProps) {
  const canRequest = permissionHints.can_request_resolution
  const canCancel = Boolean(pendingRequestId && permissionHints.can_cancel_resolution_request)
  const canApprove = Boolean(pendingRequestId && permissionHints.can_approve_resolution_request)
  const canReject = Boolean(pendingRequestId && permissionHints.can_reject_resolution_request)
  const showActions = canRequest || canCancel || canApprove || canReject

  if (events.length === 0 && !showActions) {
    return null
  }

  return (
    <TerrainCard className="relative flex max-h-[min(24rem,50vh)] flex-col overflow-hidden p-0">
      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto px-4 pt-4 pb-3">
        <SignalDetailLabel>Demande de résolution</SignalDetailLabel>

        {events.length > 0 ? (
          <ul className="space-y-2">
            {events.map((event) => (
              <li
                key={`${event.request_id}-${event.event_type}-${event.occurred_at}`}
                className="text-[12px] leading-relaxed text-[#555]"
              >
                {formatResolutionRequestHistoryLine(event)}
              </li>
            ))}
          </ul>
        ) : canRequest ? (
          <p className="text-[13px] leading-relaxed text-[#7D7B75]">
            Demandez une confirmation de résolution sans créer de plan d’action.
          </p>
        ) : null}

        {errorMessage ? <TerrainFeedback variant="error" message={errorMessage} /> : null}
      </div>

      {showActions ? (
        <div
          className={cn(
            'sticky bottom-0 z-10 flex flex-wrap gap-2 border-t border-[#E8E6DF] bg-white px-4 py-3',
          )}
        >
          {canCancel ? (
            <Button
              type="button"
              variant="outline"
              onClick={onCancel}
              disabled={isCancelPending}
            >
              Annuler la demande
            </Button>
          ) : null}
          {canApprove ? (
            <Button
              type="button"
              className="bg-[#1D9E75] text-white hover:bg-[#1D9E75]/90 focus-visible:ring-[#1D9E75]/40"
              onClick={onApprove}
              disabled={isApprovePending}
            >
              Approuver
            </Button>
          ) : null}
          {canReject ? (
            <Button
              type="button"
              className="bg-destructive text-white hover:bg-destructive/90 focus-visible:ring-destructive/40"
              onClick={onReject}
              disabled={isRejectPending}
            >
              Refuser la demande
            </Button>
          ) : null}
          {canRequest ? (
            <Button
              type="button"
              className="bg-[#114660] text-white hover:bg-[#114660]/90 focus-visible:ring-[#114660]/40"
              onClick={onCreate}
              disabled={isCreatePending}
            >
              Demander la résolution
            </Button>
          ) : null}
        </div>
      ) : null}
    </TerrainCard>
  )
}

export function resolutionRequestEventsFromDetail(
  signal: SignalDetail,
): ResolutionRequestHistoryEvent[] {
  return (signal.resolution_request_events ?? []).map((event) => ({
    request_id: event.request_id,
    event_type: event.event_type,
    occurred_at: event.occurred_at,
    actor_display_name: event.actor_display_name,
  }))
}
