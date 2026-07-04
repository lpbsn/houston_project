import type { NotificationSubjectType } from '../types'

export function resolveNotificationPath(
  subjectType: NotificationSubjectType,
  subjectId: string,
): string | null {
  switch (subjectType) {
    case 'action_plan_execution':
      return `/action-plans/executions/${subjectId}`
    case 'signal':
      return `/signals/${subjectId}`
    case 'comment':
      return null
    default:
      return null
  }
}
