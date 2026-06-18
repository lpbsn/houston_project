import type { ActionAcceptedBy, ActionMembershipRef } from '@/features/actions/types'
import type { SignalClassificationInput } from '@/lib/signal-classification'

const STATUS_LABELS: Record<string, string> = {
  open: 'À faire',
  in_progress: 'En cours',
  pending_validation: 'À valider',
  reopened: 'Rouverte',
  done: 'Terminée',
  canceled: 'Annulée',
}

const EXECUTION_FEED_STATUS_LABELS: Record<string, string> = {
  open: 'En attente',
  in_progress: 'En cours',
  pending_validation: 'À valider',
  reopened: 'Rouverte',
  done: 'Terminée',
  canceled: 'Annulée',
}

const DEADLINE_CRITICAL_REMAINING_RATIO = 0.2
const DEADLINE_CRITICAL_REMAINING_MS = 30 * 60 * 1000

/** Left border accent hex colors for action feed cards (status-only; urgency never affects this). */
export const ACTION_CARD_LEFT_ACCENT_COLOR = {
  open: '#EF9F27',
  in_progress: '#1B4FD8',
  pending_validation: '#EF9F27',
  done: '#1D9E75',
  canceled: '#555',
  reopened: '#EF9F27',
  neutral: '#7D7B75',
} as const

function getActionCardLeftAccentColorKey(status: string): keyof typeof ACTION_CARD_LEFT_ACCENT_COLOR {
  if (status === 'open') {
    return 'open'
  }
  if (status === 'in_progress') {
    return 'in_progress'
  }
  if (status === 'pending_validation') {
    return 'pending_validation'
  }
  if (status === 'done') {
    return 'done'
  }
  if (status === 'canceled') {
    return 'canceled'
  }
  if (status === 'reopened') {
    return 'reopened'
  }
  return 'neutral'
}

/** Hex color for action feed card left border (status only). */
export function getActionCardLeftAccentColor(status: string): string {
  return ACTION_CARD_LEFT_ACCENT_COLOR[getActionCardLeftAccentColorKey(status)]
}

export function shouldShowActionUrgentBadge(
  signalSummary: { urgency?: string } | null,
): boolean {
  return signalSummary?.urgency === 'high'
}

export function formatActionStatusLabel(status: string): string {
  return STATUS_LABELS[status] ?? status
}

export function formatActionExecutionFeedStatusLabel(status: string): string {
  return EXECUTION_FEED_STATUS_LABELS[status] ?? status
}

type ActionSignalSummaryLike = {
  location_text?: string | null
  [key: string]: unknown
} | null

type ActionClassificationSource = {
  affected_business_unit_key?: string | null
  affected_business_unit_label?: string | null
  responsible_business_unit_key?: string | null
  responsible_business_unit_label?: string | null
  activity_subject_normalized_name?: string | null
  activity_subject_label?: string | null
}

export function actionClassificationInput(
  action: ActionClassificationSource,
): SignalClassificationInput {
  return {
    affected_business_unit_key: action.affected_business_unit_key,
    affected_business_unit_label: action.affected_business_unit_label,
    responsible_business_unit_key: action.responsible_business_unit_key,
    responsible_business_unit_label: action.responsible_business_unit_label,
    activity_subject_normalized_name: action.activity_subject_normalized_name,
    activity_subject_label: action.activity_subject_label,
  }
}

export function getActionLocationText(signalSummary: ActionSignalSummaryLike): string | null {
  const location = signalSummary?.location_text?.trim()
  return location || null
}

export function formatActionDueLabel(dueAt: string, isOverdue: boolean): string {
  const date = new Date(dueAt)
  const formatted = date.toLocaleString('fr-FR', {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  })
  return isOverdue ? `En retard · ${formatted}` : formatted
}

export function formatActionRemainingTimeLabel(
  dueAt: string,
  isOverdue: boolean,
  now: number = Date.now(),
): string {
  if (isOverdue) {
    return '⏱ En retard'
  }

  const remainingMs = new Date(dueAt).getTime() - now
  if (remainingMs <= 0) {
    return '⏱ En retard'
  }

  const minutes = Math.ceil(remainingMs / 60000)
  if (minutes < 60) {
    return `⏱ ${minutes} min restantes`
  }

  const hours = Math.ceil(minutes / 60)
  if (hours < 24) {
    return `⏱ ${hours} h restantes`
  }

  const days = Math.ceil(hours / 24)
  return `⏱ ${days} j restantes`
}

export function formatActionDueByTimeLabel(dueAt: string): string {
  const date = new Date(dueAt)
  const hours = date.getHours()
  const minutes = date.getMinutes().toString().padStart(2, '0')
  return `avant ${hours}h${minutes}`
}

/** Remaining percent (0–100) on the created_at → due_at window for deadline bar fill. */
export function getActionDeadlineRemainingPercent(
  createdAt: string,
  dueAt: string,
  now: number = Date.now(),
): number {
  const totalMs = new Date(dueAt).getTime() - new Date(createdAt).getTime()
  if (totalMs <= 0) {
    return 0
  }

  const remainingMs = new Date(dueAt).getTime() - now
  const deadlineRemainingPercent = (remainingMs / totalMs) * 100
  return Math.min(100, Math.max(0, deadlineRemainingPercent))
}

/** Fill color for the shrinking deadline bar: green → yellow → red as time runs out. */
export const ACTION_DEADLINE_BAR_FILL_COLOR = {
  green: '#1D9E75',
  yellow: '#EF9F27',
  red: '#E24B4A',
} as const

export function getActionDeadlineBarFillColor(remainingPercent: number): string {
  const remaining = Math.min(100, Math.max(0, remainingPercent))

  if (remaining > 66.67) {
    return ACTION_DEADLINE_BAR_FILL_COLOR.green
  }
  if (remaining > 33.33) {
    return ACTION_DEADLINE_BAR_FILL_COLOR.yellow
  }
  return ACTION_DEADLINE_BAR_FILL_COLOR.red
}

export function isActionDeadlineCritical({
  dueAt,
  isOverdue,
  createdAt,
  now = Date.now(),
}: {
  dueAt: string
  isOverdue: boolean
  createdAt: string
  now?: number
}): boolean {
  if (isOverdue) {
    return true
  }

  const dueMs = new Date(dueAt).getTime()
  const remainingMs = dueMs - now
  if (remainingMs <= 0) {
    return true
  }

  if (remainingMs <= DEADLINE_CRITICAL_REMAINING_MS) {
    return true
  }

  const windowMs = dueMs - new Date(createdAt).getTime()
  if (windowMs > 0 && remainingMs / windowMs <= DEADLINE_CRITICAL_REMAINING_RATIO) {
    return true
  }

  return false
}

const MEMBERSHIP_ROLE_LABELS: Record<string, string> = {
  owner: 'Propriétaire',
  director: 'Directeur',
  manager: 'Manager',
  staff: 'Équipe',
}

export function formatMembershipRoleDisplay(role: string): string {
  return MEMBERSHIP_ROLE_LABELS[role] ?? role
}

export function getDisplayNameInitials(displayName: string): string {
  const trimmed = displayName.trim()
  if (!trimmed) {
    return '?'
  }

  const parts = trimmed.split(/\s+/).filter(Boolean)
  if (parts.length >= 2) {
    const firstInitial = parts[0][0] ?? ''
    const lastInitial = parts[parts.length - 1].replace(/\.$/, '')[0] ?? ''
    const initials = `${firstInitial}${lastInitial}`.toUpperCase()
    return initials || '?'
  }

  return trimmed.slice(0, 2).toUpperCase()
}

export function formatCompactDisplayName(displayName: string): string {
  const trimmed = displayName.trim()
  if (!trimmed) {
    return trimmed
  }

  const parts = trimmed.split(/\s+/).filter(Boolean)
  if (parts.length >= 2) {
    const lastPart = parts[parts.length - 1]
    const lastInitial = lastPart.replace(/\.$/, '')[0]
    if (lastInitial) {
      return `${parts[0]} ${lastInitial.toUpperCase()}.`
    }
  }

  return trimmed
}

export function formatActionCreatorFooterLabel(createdByDisplayName: string): string {
  const shortName = formatCompactDisplayName(createdByDisplayName)
  if (!shortName) {
    return 'Créé par —'
  }
  return `Créé par ${shortName}`
}

export function isActionPendingValidationCard(action: { status: string }): boolean {
  return action.status === 'pending_validation'
}

export function formatActionValidationWaitingLabel(canValidate: boolean): string {
  if (canValidate) {
    return 'En attente de votre validation'
  }
  return 'En attente de validation'
}

export function resolveActionValidationRelativeTimeIso(action: {
  last_activity_at: string
  marked_done_at?: string | null
}): string {
  const markedDoneAt = action.marked_done_at?.trim()
  if (markedDoneAt) {
    return markedDoneAt
  }
  return action.last_activity_at
}

export function formatActionValidationRelativeTime(
  iso: string,
  now: number = Date.now(),
): string {
  const date = new Date(iso)
  const diffMs = now - date.getTime()
  const minutes = Math.floor(diffMs / 60000)
  if (minutes < 60) {
    return `il y a ${Math.max(minutes, 1)} min`
  }
  const hours = Math.floor(minutes / 60)
  if (hours < 24) {
    return `il y a ${hours} h`
  }
  const days = Math.floor(hours / 24)
  return `il y a ${days} j`
}

export function formatActionCompletedByLabel(displayName: string): string {
  const shortName = formatCompactDisplayName(displayName)
  if (!shortName) {
    return 'Action terminée'
  }
  return `${shortName} a terminé`
}

export function formatActionAssigneesLabel(assignees: ActionMembershipRef[]): string {
  if (assignees.length === 0) {
    return '—'
  }

  const compactNames = assignees.map((assignee) => formatCompactDisplayName(assignee.display_name))
  if (assignees.length <= 2) {
    return compactNames.join(', ')
  }

  return `${compactNames[0]} +${assignees.length - 1}`
}

export function formatActionAcceptedByLabel(acceptedBy: ActionAcceptedBy | null): string {
  if (!acceptedBy?.display_name) {
    return '—'
  }
  return formatCompactDisplayName(acceptedBy.display_name) || '—'
}

export function formatActionAcceptedByFooterLabel(acceptedBy: ActionAcceptedBy | null): string {
  const shortName = formatActionAcceptedByLabel(acceptedBy)
  if (shortName === '—') {
    return 'En cours'
  }
  return `En cours · ${shortName}`
}
