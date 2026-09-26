import type {
  ActionPlanExecutionFeedAssignee,
  ActionPlanExecutionFeedItem,
} from '@/features/action-plans/types'

export type ActionPlanFeedSidebarState =
  | { variant: 'countdown'; prefix: 'DANS'; value: string }
  | { variant: 'all_day' }
  | { variant: 'no_deadline' }
  | { variant: 'overdue'; prefix: 'RETARD'; value: string }

const MS_PER_HOUR = 60 * 60 * 1000
const MS_PER_DAY = 24 * MS_PER_HOUR

function formatActionPlanFeedDuration(durationMs: number): string {
  if (!Number.isFinite(durationMs) || durationMs <= 0) {
    return '0h'
  }

  if (durationMs >= MS_PER_DAY) {
    return `${Math.floor(durationMs / MS_PER_DAY)}j`
  }

  return `${Math.max(1, Math.ceil(durationMs / MS_PER_HOUR))}h`
}

/** Compact start countdown: DÉBUT 3j / DÉBUT 7h / DÉBUT &lt;1h */
export function formatActionPlanFeedStartCountdownValue(remainingMs: number): string {
  if (!Number.isFinite(remainingMs) || remainingMs < MS_PER_HOUR) {
    return '<1h'
  }

  if (remainingMs >= MS_PER_DAY) {
    return `${Math.floor(remainingMs / MS_PER_DAY)}j`
  }

  return `${Math.ceil(remainingMs / MS_PER_HOUR)}h`
}

export function getActionPlanFeedSidebarState(
  endAt: string | null,
  now: number,
  isOverdue = false,
  allDay = false,
): ActionPlanFeedSidebarState {
  if (allDay && !isOverdue) {
    return { variant: 'all_day' }
  }
  if (isOverdue) {
    const endMs = endAt ? Date.parse(endAt) : Number.NaN
    const overdueMs = Number.isNaN(endMs) ? 0 : Math.max(0, now - endMs)
    return {
      variant: 'overdue',
      prefix: 'RETARD',
      value: formatActionPlanFeedDuration(overdueMs),
    }
  }

  if (!endAt) {
    return { variant: 'no_deadline' }
  }

  const endMs = Date.parse(endAt)
  if (Number.isNaN(endMs)) {
    return { variant: 'no_deadline' }
  }

  return {
    variant: 'countdown',
    prefix: 'DANS',
    value: formatActionPlanFeedDuration(Math.max(0, endMs - now)),
  }
}

export function formatExecutionFeedCreatedLabel(createdAt: string): string | null {
  const date = new Date(createdAt)
  if (Number.isNaN(date.getTime())) {
    return null
  }
  return `Créé le ${date.toLocaleDateString('fr-FR')}`
}

const MAX_CARD_VISIBLE_ASSIGNEES = 2
const MAX_NAMED_OTHER_POLES = 2

export function formatActionPlanFeedCardStatusLabel(
  item: Pick<ActionPlanExecutionFeedItem, 'status' | 'validated_at'>,
): string {
  switch (item.status) {
    case 'pending_validation':
      return 'À valider'
    case 'in_progress':
      return 'En cours'
    case 'scheduled':
      return 'Planifié'
    case 'done':
      return item.validated_at != null ? 'Validé' : 'Terminé'
    case 'canceled':
      return 'Annulé'
    default:
      return item.status
  }
}

export function formatActionPlanFeedCardAssigneeDisplay(
  assignees: ActionPlanExecutionFeedAssignee[],
): { visible: string[]; overflow: number; empty: boolean } {
  const names = assignees
    .map((assignee) => assignee.display_name.trim())
    .filter((name) => name.length > 0)
  if (names.length === 0) {
    return { visible: [], overflow: 0, empty: true }
  }
  return {
    visible: names.slice(0, MAX_CARD_VISIBLE_ASSIGNEES),
    overflow: Math.max(0, names.length - MAX_CARD_VISIBLE_ASSIGNEES),
    empty: false,
  }
}

type InvolvedPoleLike = {
  business_unit?: {
    id?: string
    specific_name?: string
  }
}

export function getActionPlanFeedOtherPoles(
  item: Pick<ActionPlanExecutionFeedItem, 'pilot_business_unit' | 'involved_poles'>,
): { names: string[]; overflow: number; otherCount: number } {
  const pilotId = item.pilot_business_unit.id
  const names: string[] = []
  for (const pole of item.involved_poles as InvolvedPoleLike[]) {
    const bu = pole.business_unit
    if (!bu?.id || bu.id === pilotId) {
      continue
    }
    const name = (bu.specific_name ?? '').trim()
    if (!name || names.includes(name)) {
      continue
    }
    names.push(name)
  }
  const otherCount = names.length
  return {
    names: names.slice(0, MAX_NAMED_OTHER_POLES),
    overflow: Math.max(0, otherCount - MAX_NAMED_OTHER_POLES),
    otherCount,
  }
}

export function formatActionPlanFeedOtherPolesCountLabel(otherCount: number): string {
  return otherCount === 1 ? '+1 pôle' : `+${otherCount} pôles`
}

/** Progress 0–100 along [from, to]; null if interval unusable. */
export function computeTemporalProgressPercent(
  fromIso: string | null | undefined,
  toIso: string | null | undefined,
  nowMs: number,
): number | null {
  if (!fromIso || !toIso) {
    return null
  }
  const fromMs = Date.parse(fromIso)
  const toMs = Date.parse(toIso)
  if (Number.isNaN(fromMs) || Number.isNaN(toMs) || fromMs >= toMs) {
    return null
  }
  if (nowMs <= fromMs) {
    return 0
  }
  if (nowMs >= toMs) {
    return 100
  }
  return Math.round(((nowMs - fromMs) / (toMs - fromMs)) * 100)
}

export function formatActionPlanFeedCardDelayLabel(
  endAt: string | null,
  now: number,
  isOverdue: boolean,
): string | null {
  if (!isOverdue) {
    return null
  }
  const state = getActionPlanFeedSidebarState(endAt, now, true, false)
  if (state.variant !== 'overdue') {
    return null
  }
  return `Retard ${state.value}`
}

export function formatActionPlanFeedStartsInLabel(
  startAt: string | null,
  now: number,
): string | null {
  if (!startAt) {
    return null
  }
  const startMs = Date.parse(startAt)
  if (Number.isNaN(startMs)) {
    return null
  }
  const remaining = startMs - now
  if (remaining <= 0) {
    return null
  }
  return `Début dans ${formatActionPlanFeedStartCountdownValue(remaining).replace('<', '< ')}`
}

function formatProchaineMoment(startAt: string, allDay: boolean, now: Date): string | null {
  const start = new Date(startAt)
  if (Number.isNaN(start.getTime())) {
    return null
  }
  const startDay = new Date(start.getFullYear(), start.getMonth(), start.getDate())
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const tomorrow = new Date(today)
  tomorrow.setDate(tomorrow.getDate() + 1)

  let dayPart: string
  if (startDay.getTime() === today.getTime()) {
    dayPart = 'aujourd’hui'
  } else if (startDay.getTime() === tomorrow.getTime()) {
    dayPart = 'demain'
  } else {
    dayPart = start.toLocaleDateString('fr-FR', {
      weekday: 'short',
      day: 'numeric',
      month: 'short',
    })
  }

  if (allDay) {
    return `${dayPart} · Journée entière`
  }
  const timePart = start.toLocaleTimeString('fr-FR', {
    hour: '2-digit',
    minute: '2-digit',
  })
  return `${dayPart} · ${timePart}`
}

export function formatPlanifieesProchaineLabel(
  item: Pick<ActionPlanExecutionFeedItem, 'start_at' | 'all_day'> | null | undefined,
  now: Date = new Date(),
): string | null {
  if (!item?.start_at) {
    return null
  }
  const moment = formatProchaineMoment(item.start_at, item.all_day, now)
  return moment ? `Prochaine : ${moment}` : null
}

export function formatActionPlanFeedCardDateTimeLabel(
  iso: string | null | undefined,
  allDay = false,
): string | null {
  if (!iso) {
    return null
  }
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) {
    return null
  }
  if (allDay) {
    return date.toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' })
  }
  return `${date.toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' })} · ${date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}`
}

export function formatActionPlanFeedTerminalDateLabel(
  item: Pick<ActionPlanExecutionFeedItem, 'status' | 'marked_done_at' | 'canceled_at'>,
): string | null {
  if (item.status === 'done' && item.marked_done_at) {
    const label = formatActionPlanFeedCardDateTimeLabel(item.marked_done_at)
    return label ? `Terminé le ${label}` : null
  }
  if (item.status === 'canceled' && item.canceled_at) {
    const date = new Date(item.canceled_at)
    if (Number.isNaN(date.getTime())) {
      return null
    }
    return `Annulé le ${date.toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' })}`
  }
  return null
}

/** Date first; optional actor only when present. Never hide a reliable date. */
function formatActionPlanFeedActorDateLine(
  prefix: string,
  at: string | null | undefined,
  byDisplayName: string | null | undefined,
): string | null {
  if (!at) {
    return null
  }
  const dateLabel = formatActionPlanFeedCardDateTimeLabel(at)
  if (!dateLabel) {
    return null
  }
  const actor = byDisplayName?.trim()
  if (actor) {
    return `${prefix} ${dateLabel} par ${actor}`
  }
  return `${prefix} ${dateLabel}`
}

export function formatActionPlanFeedValidatedLine(
  item: Pick<
    ActionPlanExecutionFeedItem,
    'validated_at' | 'validated_by_display_name'
  >,
): string | null {
  return formatActionPlanFeedActorDateLine(
    'Validé le',
    item.validated_at,
    item.validated_by_display_name,
  )
}

export function formatActionPlanFeedMarkedDoneLine(
  item: Pick<
    ActionPlanExecutionFeedItem,
    'marked_done_at' | 'marked_done_by_display_name'
  >,
): string | null {
  return formatActionPlanFeedActorDateLine(
    'Marqué comme terminé le',
    item.marked_done_at,
    item.marked_done_by_display_name,
  )
}

export function groupScheduledItemsByStartDate(
  items: ActionPlanExecutionFeedItem[],
  now: Date = new Date(),
): { key: string; label: string; items: ActionPlanExecutionFeedItem[] }[] {
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const tomorrow = new Date(today)
  tomorrow.setDate(tomorrow.getDate() + 1)
  const groups: { key: string; label: string; items: ActionPlanExecutionFeedItem[] }[] = []
  const indexByKey = new Map<string, number>()

  for (const item of items) {
    if (!item.start_at) {
      continue
    }
    const start = new Date(item.start_at)
    if (Number.isNaN(start.getTime())) {
      continue
    }
    const day = new Date(start.getFullYear(), start.getMonth(), start.getDate())
    const key = `${day.getFullYear()}-${day.getMonth()}-${day.getDate()}`
    let label: string
    if (day.getTime() === today.getTime()) {
      label = 'Aujourd’hui'
    } else if (day.getTime() === tomorrow.getTime()) {
      label = 'Demain'
    } else {
      label = start.toLocaleDateString('fr-FR', {
        weekday: 'short',
        day: 'numeric',
        month: 'short',
      })
    }
    const existing = indexByKey.get(key)
    if (existing === undefined) {
      indexByKey.set(key, groups.length)
      groups.push({ key, label, items: [item] })
    } else {
      groups[existing]!.items.push(item)
    }
  }
  return groups
}
