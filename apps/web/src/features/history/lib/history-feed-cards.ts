import type { ExecutionFeedCardItem } from '@/features/execution/components/action-plan-execution-feed-card'
import type { SignalFeedCardDisplay } from '@/features/signals/components/signal-card'

import type { ExecutionHistoryItem, SignalHistoryItem } from '../api'

export function signalHistoryCardItem(item: SignalHistoryItem): SignalFeedCardDisplay {
  return {
    id: item.id,
    title: item.title,
    status: item.status,
    location_text: item.location_text,
    last_activity_at: item.last_activity_at,
    aggregation_count: item.aggregation_count,
    resolution_request: null,
    affected_business_unit_id: item.affected_business_unit_id,
    affected_business_unit_key: null,
    affected_business_unit_label: item.affected_business_unit_label,
    responsible_business_unit_id: item.responsible_business_unit_id,
    responsible_business_unit_key: null,
    responsible_business_unit_label: item.responsible_business_unit_label,
    activity_subject_label: item.activity_subject_label,
    activity_subject_normalized_name: item.activity_subject_normalized_name,
    establishment_name: item.establishment_name,
    reporter_display_name: item.reporter_display_name,
  }
}

export function executionHistoryCardItem(item: ExecutionHistoryItem): ExecutionFeedCardItem {
  return {
    id: item.id,
    title: item.title,
    status: item.status,
    pilot_business_unit: item.pilot_business_unit,
    involved_poles: item.involved_poles,
    assignees: item.assignees,
    start_at: item.start_at,
    end_at: item.end_at,
    all_day: item.all_day,
    validated_at: item.validated_at,
    validated_by_display_name: item.validated_by_display_name,
    marked_done_at: item.marked_done_at,
    marked_done_by_display_name: null,
    canceled_at: item.canceled_at,
    canceled_by_display_name:
      item.status === 'canceled' ? item.termination_actor_display_name : null,
    active_review: item.active_review,
    created_at: item.created_at,
    created_by_display_name: item.created_by_display_name,
    is_overdue: false,
    visible_from: null,
  }
}
