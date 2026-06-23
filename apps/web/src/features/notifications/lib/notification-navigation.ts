import type { NotificationSubjectType } from '../types'

export function resolveNotificationPath(
  subjectType: NotificationSubjectType,
  subjectId: string,
): string | null {
  switch (subjectType) {
    case 'action':
      return `/actions/${subjectId}`
    case 'checklist_execution':
      return `/checklists/executions/${subjectId}`
    case 'signal':
      return `/signals/${subjectId}`
    case 'comment':
      return null
    default:
      return null
  }
}
