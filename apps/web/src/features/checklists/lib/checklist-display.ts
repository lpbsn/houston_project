import { formatTimePartsFromDate } from '@/features/actions/lib/action-create-deadline'
import type { ChecklistFeedItem, ChecklistTaskExecution } from '@/features/checklists/types'

export function formatChecklistExecutionStatusLabel(status: string): string {
  switch (status) {
    case 'assigned':
      return 'À faire'
    case 'in_progress':
      return 'En cours'
    case 'done':
      return 'Terminée'
    case 'canceled':
      return 'Annulée'
    default:
      return status
  }
}

export function formatChecklistTaskStatusLabel(status: string): string {
  switch (status) {
    case 'pending':
      return 'À traiter'
    case 'done':
      return 'Terminée'
    case 'skipped':
      return 'Passée'
    case 'observation_created':
      return 'Observation créée'
    default:
      return status
  }
}

export function formatChecklistProgressLabel(
  treatedCount: number,
  totalCount: number,
): string {
  return `${treatedCount}/${totalCount}`
}

export function isChecklistTaskPending(task: ChecklistTaskExecution): boolean {
  return task.status === 'pending'
}

export function formatChecklistFeedBadgeLabel(): string {
  return 'Checklist'
}

export function getChecklistFeedSection(
  item: ChecklistFeedItem,
): 'todo' | 'in_progress' | null {
  if (item.status === 'assigned') {
    return 'todo'
  }
  if (item.status === 'in_progress') {
    return 'in_progress'
  }
  return null
}

export function isChecklistExecutionOverdue(
  endAt: string | null,
  isTerminal: boolean,
): boolean {
  if (!endAt || isTerminal) {
    return false
  }
  return Date.parse(endAt) < Date.now()
}

export function formatChecklistEndAtLabel(endAt: string | null): string | null {
  if (!endAt) {
    return null
  }
  const date = new Date(endAt)
  if (Number.isNaN(date.getTime())) {
    return null
  }
  return date.toLocaleString('fr-FR', {
    dateStyle: 'short',
    timeStyle: 'short',
  })
}

export function formatChecklistEndBeforeTimeLabel(endAt: string | null): string | null {
  if (!endAt) {
    return null
  }
  const date = new Date(endAt)
  if (Number.isNaN(date.getTime())) {
    return null
  }
  const { hours, minutes } = formatTimePartsFromDate(date)
  return `Avant ${hours}:${minutes}`
}

export function formatChecklistDeadlinePillLabel(endAt: string | null): string | null {
  if (!endAt) {
    return null
  }
  const date = new Date(endAt)
  if (Number.isNaN(date.getTime())) {
    return null
  }
  const { hours, minutes } = formatTimePartsFromDate(date)
  return `avant ${hours}h${minutes}`
}

export function countChecklistTreatedTasks(tasks: ChecklistTaskExecution[]): number {
  return tasks.filter((task) => task.status !== 'pending').length
}

export function getChecklistTaskProgressPercent(
  treatedCount: number,
  totalCount: number,
): number {
  if (totalCount <= 0) {
    return 0
  }
  return Math.round((treatedCount / totalCount) * 100)
}

export function formatChecklistProgressPointsLabel(
  treatedCount: number,
  totalCount: number,
): string {
  return `${treatedCount} / ${totalCount} points`
}

export function formatChecklistProgressPercentLabel(
  treatedCount: number,
  totalCount: number,
): string {
  return `${getChecklistTaskProgressPercent(treatedCount, totalCount)}%`
}
