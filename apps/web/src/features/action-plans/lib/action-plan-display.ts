import type { SignalClassificationInput } from '@/lib/signal-classification'

import type { ActionPlanBusinessUnit } from '@/features/action-plans/types'

/** Primary display name for nested Action Plan BusinessUnit (Lot 5). */
export function actionPlanBusinessUnitPrimaryLabel(
  unit: Pick<ActionPlanBusinessUnit, 'specific_name'>,
): string {
  return unit.specific_name
}

/** Secondary context label (catalog generic). */
export function actionPlanBusinessUnitGenericLabel(
  unit: Pick<ActionPlanBusinessUnit, 'generic'>,
): string {
  return unit.generic.label
}


import type {
  ActionPlanAssigneesByPole,
  ActionPlanDetail,
  ActionPlanExecutionDetail,
  ActionPlanListItem,
  ActionPlanTaskExecution,
  ActionPlanTaskTemplate,
} from '../types'

export function formatActionPlanExecutionStatusLabel(status: string): string {
  switch (status) {
    case 'in_progress':
      return 'En cours'
    case 'pending_validation':
      return 'En attente de validation'
    case 'scheduled':
      return 'Planifiée'
    case 'done':
      return 'Terminé'
    case 'canceled':
      return 'Annulé'
    default:
      return status
  }
}

export function formatActionPlanTaskStatusLabel(status: string): string {
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

export function formatContributionStatusLabel(status: string | null | undefined): string | null {
  if (!status) {
    return null
  }
  switch (status) {
    case 'in_progress':
      return 'En cours'
    case 'done':
      return 'Terminé'
    case 'not_started':
      return 'Non démarré'
    default:
      return status
  }
}

export function formatCatalogStatusLabel(status: string | null): string {
  switch (status) {
    case 'active':
      return 'Actif'
    case 'inactive':
      return 'Inactif'
    default:
      return '—'
  }
}

export function isActionPlanTaskPending(task: ActionPlanTaskExecution): boolean {
  return task.status === 'pending'
}

export function isActionPlanExecutionTerminal(status: string): boolean {
  return status === 'done' || status === 'canceled'
}

export function isActionPlanExecutionOverdue(
  endAt: string | null,
  isTerminal: boolean,
): boolean {
  if (!endAt || isTerminal) {
    return false
  }
  return Date.parse(endAt) < Date.now()
}

export function formatActionPlanEndAtLabel(endAt: string | null): string | null {
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

export function formatActionPlanCreatedAtLabel(createdAt: string | null): string | null {
  return formatActionPlanEndAtLabel(createdAt)
}

export type ActionPlanExecutionAssignee = {
  membership_id: string
  display_name: string
}

export function flattenActionPlanAssignees(
  assigneesByPole: ActionPlanAssigneesByPole[],
): ActionPlanExecutionAssignee[] {
  const seen = new Set<string>()
  const assignees: ActionPlanExecutionAssignee[] = []

  for (const group of assigneesByPole) {
    for (const assignee of group.assignees) {
      if (seen.has(assignee.membership_id)) {
        continue
      }
      seen.add(assignee.membership_id)
      assignees.push({
        membership_id: assignee.membership_id,
        display_name: assignee.display_name,
      })
    }
  }

  return assignees
}

export type ActionPlanExecutionClassificationDisplay = {
  poleLabel: string | null
  subjectLabel: string | null
}

export function buildActionPlanExecutionClassificationDisplay(
  execution: Pick<
    ActionPlanExecutionDetail,
    'pilot_business_unit' | 'responsible_business_unit' | 'activity_subject'
  >,
): ActionPlanExecutionClassificationDisplay {
  const poleUnit = execution.responsible_business_unit ?? execution.pilot_business_unit
  const poleLabel = actionPlanBusinessUnitPrimaryLabel(poleUnit).trim() || null
  const subjectLabel = execution.activity_subject?.label?.trim() || null

  return { poleLabel, subjectLabel }
}

export function buildActionPlanExecutionClassificationInput(
  execution: Pick<
    ActionPlanExecutionDetail,
    | 'pilot_business_unit'
    | 'responsible_business_unit'
    | 'affected_business_unit'
    | 'activity_subject'
  >,
): SignalClassificationInput {
  const responsible = execution.responsible_business_unit ?? execution.pilot_business_unit
  return {
    responsible_business_unit_key: responsible.generic.key,
    responsible_business_unit_label: actionPlanBusinessUnitPrimaryLabel(responsible),
    affected_business_unit_key: execution.affected_business_unit?.generic.key ?? null,
    affected_business_unit_label: execution.affected_business_unit
      ? actionPlanBusinessUnitPrimaryLabel(execution.affected_business_unit)
      : null,
    activity_subject_key: execution.activity_subject?.catalog_key ?? null,
    activity_subject_label: execution.activity_subject?.label ?? null,
    activity_subject_normalized_name: null,
  }
}

export type ActionPlanPoleTaskSummary = {
  businessUnitId: string
  label: string
  role: 'pilot' | 'contributor'
  treated: number
  total: number
}

export function buildActionPlanPoleTaskSummaries(
  execution: Pick<ActionPlanExecutionDetail, 'pilot_business_unit' | 'task_executions'>,
): ActionPlanPoleTaskSummary[] {
  const grouped = new Map<string, { label: string; tasks: ActionPlanTaskExecution[] }>()

  for (const task of execution.task_executions) {
    const businessUnitId = task.business_unit.id
    const existing = grouped.get(businessUnitId)
    if (existing) {
      existing.tasks.push(task)
      continue
    }
    grouped.set(businessUnitId, {
      label: actionPlanBusinessUnitPrimaryLabel(task.business_unit),
      tasks: [task],
    })
  }

  const summaries = Array.from(grouped.entries()).map(([businessUnitId, entry]) => ({
    businessUnitId,
    label: entry.label,
    role:
      businessUnitId === execution.pilot_business_unit.id
        ? ('pilot' as const)
        : ('contributor' as const),
    treated: countActionPlanTreatedTasks(entry.tasks),
    total: entry.tasks.length,
  }))

  return summaries.sort((left, right) => {
    if (left.role !== right.role) {
      return left.role === 'pilot' ? -1 : 1
    }
    return left.label.localeCompare(right.label, 'fr')
  })
}

export function buildActionPlanTemplatePoleSummaries(
  plan: Pick<ActionPlanDetail, 'pilot_business_unit' | 'tasks'>,
): ActionPlanPoleTaskSummary[] {
  const grouped = new Map<string, { label: string; tasks: ActionPlanTaskTemplate[] }>()

  for (const task of plan.tasks) {
    const businessUnitId = task.business_unit.id
    const existing = grouped.get(businessUnitId)
    if (existing) {
      existing.tasks.push(task)
      continue
    }
    grouped.set(businessUnitId, {
      label: actionPlanBusinessUnitPrimaryLabel(task.business_unit),
      tasks: [task],
    })
  }

  const summaries = Array.from(grouped.entries()).map(([businessUnitId, entry]) => ({
    businessUnitId,
    label: entry.label,
    role:
      businessUnitId === plan.pilot_business_unit.id
        ? ('pilot' as const)
        : ('contributor' as const),
    treated: 0,
    total: entry.tasks.length,
  }))

  return summaries.sort((left, right) => {
    if (left.role !== right.role) {
      return left.role === 'pilot' ? -1 : 1
    }
    return left.label.localeCompare(right.label, 'fr')
  })
}

export type ActionPlanDeadlineState = {
  mode: 'progress' | 'simple'
  progressPct: number | null
  remainingLabel: string | null
  beforeLabel: string | null
  endAtLabel: string | null
  isOverdue: boolean
}

function formatActionPlanDeadlineBeforeLabel(endAt: string): string | null {
  const date = new Date(endAt)
  if (Number.isNaN(date.getTime())) {
    return null
  }
  const timeLabel = date.toLocaleTimeString('fr-FR', {
    hour: '2-digit',
    minute: '2-digit',
  })
  return `avant ${timeLabel}`
}

const MS_PER_MINUTE = 60_000
const MS_PER_HOUR = 60 * MS_PER_MINUTE
const MS_PER_DAY = 24 * MS_PER_HOUR

function formatActionPlanRemainingTimeLabel(remainingMs: number): string {
  if (remainingMs >= MS_PER_DAY) {
    const days = Math.ceil(remainingMs / MS_PER_DAY)
    return days === 1 ? '1 jour restant' : `${days} jours restants`
  }
  if (remainingMs >= MS_PER_HOUR) {
    const hours = Math.floor(remainingMs / MS_PER_HOUR)
    const minutes = Math.floor((remainingMs % MS_PER_HOUR) / MS_PER_MINUTE)
    const timePart = minutes > 0 ? `${hours}h ${minutes}min` : `${hours}h`
    return `${timePart} restante${hours > 1 || minutes > 0 ? 's' : ''}`
  }
  const remainingMinutes = Math.max(1, Math.ceil(remainingMs / MS_PER_MINUTE))
  return `${remainingMinutes} min restante${remainingMinutes > 1 ? 's' : ''}`
}

export function computeActionPlanDeadlineState(options: {
  startAt: string | null
  endAt: string | null
  isTerminal: boolean
  now?: number
}): ActionPlanDeadlineState | null {
  const { startAt, endAt, isTerminal, now = Date.now() } = options
  if (!endAt) {
    return null
  }

  const endAtLabel = formatActionPlanEndAtLabel(endAt)
  const isOverdue = isActionPlanExecutionOverdue(endAt, isTerminal)

  if (!startAt || isTerminal) {
    return {
      mode: 'simple',
      progressPct: null,
      remainingLabel: null,
      beforeLabel: null,
      endAtLabel,
      isOverdue,
    }
  }

  const startMs = Date.parse(startAt)
  const endMs = Date.parse(endAt)
  if (Number.isNaN(startMs) || Number.isNaN(endMs) || endMs <= startMs) {
    return {
      mode: 'simple',
      progressPct: null,
      remainingLabel: null,
      beforeLabel: formatActionPlanDeadlineBeforeLabel(endAt),
      endAtLabel,
      isOverdue,
    }
  }

  const totalMs = endMs - startMs
  const elapsedMs = Math.max(0, now - startMs)
  const progressPct = Math.min(100, Math.max(0, Math.round((elapsedMs / totalMs) * 100)))
  const remainingMs = endMs - now

  return {
    mode: 'progress',
    progressPct,
    remainingLabel:
      remainingMs > 0
        ? formatActionPlanRemainingTimeLabel(remainingMs)
        : 'Échéance dépassée',
    beforeLabel: formatActionPlanDeadlineBeforeLabel(endAt),
    endAtLabel,
    isOverdue,
  }
}

export function formatActionPlanTaskDeadlineLabel(deadlineAt: string | null | undefined): string | null {
  if (!deadlineAt) {
    return null
  }
  return formatActionPlanEndAtLabel(deadlineAt)
}

function joinActionPlanTaskMetaParts(parts: string[]): string | null {
  return parts.length > 0 ? parts.join(' · ') : null
}

export function formatActionPlanTaskAssigneePoleLine(options: {
  assigneeDisplayName?: string | null
  poleLabel?: string | null
}): string | null {
  const parts: string[] = []
  if (options.assigneeDisplayName) {
    parts.push(options.assigneeDisplayName)
  }
  if (options.poleLabel) {
    parts.push(options.poleLabel)
  }
  return parts.length > 0 ? parts.join(' - ') : null
}

export function formatActionPlanTaskEditorMetaLine(options: {
  assigneeDisplayName?: string | null
  deadlineAt?: string | null
}): string | null {
  const parts: string[] = []
  if (options.assigneeDisplayName) {
    parts.push(options.assigneeDisplayName)
  }
  const deadlineLabel = formatActionPlanTaskDeadlineLabel(options.deadlineAt)
  if (deadlineLabel) {
    parts.push(deadlineLabel)
  }
  return joinActionPlanTaskMetaParts(parts)
}

export function countActionPlanTreatedTasks(tasks: ActionPlanTaskExecution[]): number {
  return tasks.filter((task) => task.status !== 'pending').length
}

export type ActionPlanCatalogSection = {
  businessUnitId: string
  businessUnitLabel: string
  items: ActionPlanListItem[]
}

export function groupActionPlansByPilotBusinessUnit(
  items: ActionPlanListItem[],
): ActionPlanCatalogSection[] {
  const sections = new Map<string, ActionPlanCatalogSection>()
  for (const item of items) {
    const businessUnitId = item.pilot_business_unit.id
    const existing = sections.get(businessUnitId)
    if (existing) {
      existing.items.push(item)
      continue
    }
    sections.set(businessUnitId, {
      businessUnitId,
      businessUnitLabel: actionPlanBusinessUnitPrimaryLabel(item.pilot_business_unit),
      items: [item],
    })
  }
  return Array.from(sections.values()).sort((a, b) =>
    a.businessUnitLabel.localeCompare(b.businessUnitLabel, 'fr'),
  )
}

export function truncateActionPlanDescription(description: string, maxLength = 120): string {
  const trimmed = description.trim()
  if (trimmed.length <= maxLength) {
    return trimmed
  }
  return `${trimmed.slice(0, maxLength - 1)}…`
}
