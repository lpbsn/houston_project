import { buildCommentDeepLinkPath, buildExecutionValidationFocusPath } from '@/features/comments/lib/detail-deep-link'

import type { NotificationItem } from '../types'

export function resolveNotificationPath(notification: NotificationItem): string | null {
  const { subject_type: subjectType, subject_id: subjectId, event_key: eventKey, navigation } =
    notification

  switch (subjectType) {
    case 'action_plan_execution':
      if (eventKey === 'action_plan.execution.pending_validation') {
        return buildExecutionValidationFocusPath(subjectId)
      }
      return `/action-plans/executions/${subjectId}`
    case 'signal':
      return `/signals/${subjectId}`
    case 'chat_conversation':
      return `/chat/${subjectId}`
    case 'comment': {
      if (!navigation) {
        return null
      }

      if (navigation.parent_subject_type === 'signal') {
        return buildCommentDeepLinkPath(`/signals/${navigation.parent_subject_id}`, subjectId)
      }

      if (navigation.parent_subject_type === 'action_plan_execution') {
        return buildCommentDeepLinkPath(
          `/action-plans/executions/${navigation.parent_subject_id}`,
          subjectId,
        )
      }

      return null
    }
    default:
      return null
  }
}
