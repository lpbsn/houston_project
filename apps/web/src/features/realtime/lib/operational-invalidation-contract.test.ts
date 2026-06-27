import { describe, expect, it, vi } from 'vitest'

import { applyOperationalInvalidation } from '@/features/realtime/lib/apply-operational-invalidation'
import {
  notificationInvalidationReasons,
  operationalInvalidationEventPairs,
  operationalInvalidationEvents,
  reasonGatedOperationalInvalidationEvents,
} from '@/features/realtime/lib/operational-invalidation-contract'
import type { OperationalRealtimeInvalidateEvent } from '@/features/realtime/types'
import { queryClient } from '@/lib/query-client'

const COMMENT_INVALIDATION_REASONS = new Set([
  'comment.signal.created',
  'comment.signal.inherited',
  'comment.action.created',
  'comment.action.resolved',
  'comment.action.unresolved',
])

function buildEvent(
  subject_type: OperationalRealtimeInvalidateEvent['subject_type'],
  reason: string,
  entityId = 'entity-1',
): OperationalRealtimeInvalidateEvent {
  return {
    type: 'invalidate',
    subject_type,
    reason,
    establishment_id: 'est-1',
    entity_id: entityId,
    occurred_at: '2026-06-19T12:00:00Z',
  }
}

describe('operational invalidation contract', () => {
  it('loads the expected number of operational events', () => {
    expect(operationalInvalidationEvents).toHaveLength(15)
    expect(operationalInvalidationEventPairs).toHaveLength(15)
  })

  it.each(operationalInvalidationEventPairs)(
    'applyOperationalInvalidation handles contract event %s / %s',
    (subject_type, reason) => {
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')
      const entityId =
        subject_type === 'comment' && reason === 'comment.signal.created' ? 'sig-1' : 'entity-1'

      applyOperationalInvalidation(buildEvent(subject_type, reason, entityId), {
        queryClient,
        establishmentId: 'est-1',
      })

      expect(invalidateSpy).toHaveBeenCalled()
      invalidateSpy.mockRestore()
    },
  )

  it('frontend comment invalidation reasons are covered by the contract', () => {
    const contractCommentReasons = new Set(
      reasonGatedOperationalInvalidationEvents
        .filter((event) => event.subject_type === 'comment')
        .map((event) => event.reason),
    )
    expect(COMMENT_INVALIDATION_REASONS).toEqual(contractCommentReasons)
  })

  it('frontend notification invalidation reasons are covered by the contract', () => {
    expect(notificationInvalidationReasons).toEqual(
      new Set([
        'notification.created',
        'notification.updated',
        'notification.bulk_updated',
      ]),
    )
  })

  it('contract reason-gated events match frontend handler coverage', () => {
    const contractReasonGatedPairs = new Set(
      reasonGatedOperationalInvalidationEvents.map(
        (event) => `${event.subject_type}:${event.reason}`,
      ),
    )
    const frontendReasonGatedPairs = new Set([
      ...[...COMMENT_INVALIDATION_REASONS].map((reason) => `comment:${reason}`),
      ...[...notificationInvalidationReasons].map((reason) => `notification:${reason}`),
    ])
    expect(frontendReasonGatedPairs).toEqual(contractReasonGatedPairs)
  })
})
