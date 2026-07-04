import type {
  ActionPlanAssigneesByPole,
  ActionPlanExecutionDetail,
  ActionPlanInvolvedPole,
  ActionPlanListItem,
  ActionPlanTaskExecution,
} from '../types'

export function formatActionPlanExecutionStatusLabel(status: string): string {
  switch (status) {
    case 'in_progress':
      return 'En cours'
    case 'pending_validation':
      return 'En attente de validation'
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
      businessUnitLabel: item.pilot_business_unit.label,
      items: [item],
    })
  }
  return Array.from(sections.values()).sort((a, b) =>
    a.businessUnitLabel.localeCompare(b.businessUnitLabel, 'fr'),
  )
}

export type ActionPlanPoleSection = {
  businessUnitId: string
  businessUnitLabel: string
  contributionStatus: string | null
  assignees: ActionPlanAssigneesByPole['assignees']
  tasks: ActionPlanTaskExecution[]
}

export function buildActionPlanPoleSections(
  execution: ActionPlanExecutionDetail,
): ActionPlanPoleSection[] {
  const assigneesByPole = new Map(
    execution.assignees_by_pole.map((pole) => [pole.business_unit.id, pole.assignees]),
  )
  const contributionByPole = new Map(
    execution.involved_poles.map((pole: ActionPlanInvolvedPole) => [
      pole.business_unit.id,
      pole.contribution_status,
    ]),
  )
  const tasksByPole = new Map<string, ActionPlanTaskExecution[]>()
  for (const task of execution.task_executions) {
    const businessUnitId = task.business_unit.id
    const existing = tasksByPole.get(businessUnitId) ?? []
    existing.push(task)
    tasksByPole.set(businessUnitId, existing)
  }

  const poleIds = new Set<string>([
    ...assigneesByPole.keys(),
    ...tasksByPole.keys(),
  ])

  const sections: ActionPlanPoleSection[] = []
  for (const businessUnitId of Array.from(poleIds).sort()) {
    const tasks = (tasksByPole.get(businessUnitId) ?? []).sort(
      (a, b) => a.position - b.position,
    )
    const assigneePole = execution.assignees_by_pole.find(
      (pole) => pole.business_unit.id === businessUnitId,
    )
    const taskPole = tasks[0]?.business_unit
    sections.push({
      businessUnitId,
      businessUnitLabel:
        assigneePole?.business_unit.label ?? taskPole?.label ?? businessUnitId,
      contributionStatus: contributionByPole.get(businessUnitId) ?? null,
      assignees: assigneesByPole.get(businessUnitId) ?? [],
      tasks,
    })
  }

  return sections.sort((a, b) => a.businessUnitLabel.localeCompare(b.businessUnitLabel, 'fr'))
}

export function truncateActionPlanDescription(description: string, maxLength = 120): string {
  const trimmed = description.trim()
  if (trimmed.length <= maxLength) {
    return trimmed
  }
  return `${trimmed.slice(0, maxLength - 1)}…`
}
