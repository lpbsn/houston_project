import type { ActionPlanCreateMode } from './action-plan-create-mode'
import {
  resolveCatalogPlanningSubmit,
  type CatalogPlanningOptions,
} from './action-plan-catalog-planning-submit'
import {
  hasGlobalRepeat,
  toSharedChronologyFields,
  type ActionPlanEventPlanningDraft,
} from './action-plan-event-planning-form'

export const ACTION_PLAN_DESKTOP_SAVE_LABEL = 'Enregistrer'
export const ACTION_PLAN_DESKTOP_START_LABEL = 'Démarrer'
export const ACTION_PLAN_DESKTOP_SCHEDULE_LABEL = 'Programmer'
export const ACTION_PLAN_DESKTOP_USE_LABEL = 'Utiliser'
export const ACTION_PLAN_DESKTOP_PILOT_LABEL = 'Pôle pilote'
export const ACTION_PLAN_DESKTOP_END_LABEL = 'Échéance'

export const actionPlanDesktopInputClassName =
  'h-10 rounded-lg border-transparent bg-[#F5F4F0] shadow-none'
export const actionPlanDesktopTextareaClassName =
  'min-h-20 rounded-lg border-transparent bg-[#F5F4F0] shadow-none'

const JOURNEY_TITLE: Record<ActionPlanCreateMode | 'execution-edit', string> = {
  catalog: 'Créer un modèle',
  execution: 'Créer une exécution',
  'signal-linked': 'Exécution liée à l’observation',
  'template-edit': 'Modifier le modèle',
  'execution-edit': 'Modifier l’exécution',
}

export function resolveActionPlanDesktopJourneyTitle(
  mode: ActionPlanCreateMode | 'execution-edit',
): string {
  return JOURNEY_TITLE[mode]
}

/**
 * Desktop web fixes the library outcome from the route.
 * Mobile keeps the toggle value.
 */
export function resolveDesktopLibraryPersistence(
  mode: ActionPlanCreateMode | 'execution-edit',
  saveToLibrary: boolean,
  isDesktopWeb: boolean,
): boolean {
  if (!isDesktopWeb || mode === 'execution-edit') {
    return saveToLibrary
  }
  return mode === 'catalog'
}

/** Matches the 5-minute snap used by “Maintenant”, so that slot still starts now. */
const IMMEDIATE_START_TOLERANCE_MS = 5 * 60 * 1000

export type DesktopLaunchOutcome = {
  executions: number
  schedules: number
  hasFutureStart: boolean
}

const EMPTY_LAUNCH_OUTCOME: DesktopLaunchOutcome = {
  executions: 0,
  schedules: 0,
  hasFutureStart: false,
}

function executionStartIsFuture(startAt: string | null | undefined, now: Date): boolean {
  if (!startAt?.trim()) {
    return false
  }
  const parsed = Date.parse(startAt)
  if (Number.isNaN(parsed)) {
    return false
  }
  return parsed > now.getTime() + IMMEDIATE_START_TOLERANCE_MS
}

function summarizePlanningItems(
  draft: ActionPlanEventPlanningDraft,
  options: CatalogPlanningOptions,
  now: Date,
): DesktopLaunchOutcome {
  const submit = resolveCatalogPlanningSubmit(draft, options)
  if (!submit) {
    return EMPTY_LAUNCH_OUTCOME
  }

  let executions = 0
  let schedules = 0
  let hasFutureStart = false
  for (const item of submit.body.items) {
    if (item.kind === 'schedule') {
      schedules += 1
      continue
    }
    executions += 1
    if (executionStartIsFuture(item.start_at, now)) {
      hasFutureStart = true
    }
  }
  return { executions, schedules, hasFutureStart }
}

/** Same branches as the direct-create submit: library, per-assignee planning, or one shared resource. */
export function summarizeDirectCreateLaunch(
  draft: ActionPlanEventPlanningDraft,
  options: { saveToLibrary: boolean; staffMode: boolean },
  now: Date = new Date(),
): DesktopLaunchOutcome {
  if (options.saveToLibrary) {
    return EMPTY_LAUNCH_OUTCOME
  }
  if (draft.usePerAssigneeChronology && !options.staffMode) {
    return summarizePlanningItems(draft, { canSchedule: true, staffMode: false }, now)
  }
  if (hasGlobalRepeat(draft)) {
    return { executions: 0, schedules: 1, hasFutureStart: false }
  }
  const { sharedStartAt } = toSharedChronologyFields(draft)
  return {
    executions: 1,
    schedules: 0,
    hasFutureStart: executionStartIsFuture(sharedStartAt, now),
  }
}

/** Same items as a catalog “Utiliser / Programmer” submit. */
export function summarizeCatalogPlanningLaunch(
  draft: ActionPlanEventPlanningDraft,
  options: CatalogPlanningOptions,
  now: Date = new Date(),
): DesktopLaunchOutcome {
  return summarizePlanningItems(draft, options, now)
}

export function resolveDesktopLaunchLabel(outcome: DesktopLaunchOutcome): string {
  if (outcome.schedules > 0 || outcome.hasFutureStart) {
    return ACTION_PLAN_DESKTOP_SCHEDULE_LABEL
  }
  return ACTION_PLAN_DESKTOP_START_LABEL
}

function resourcePhrase(count: number, singular: string, plural: string): string {
  return `${count} ${count === 1 ? singular : plural}`
}

export function formatActionPlanSubmissionNotice(outcome: DesktopLaunchOutcome): string | null {
  if (outcome.executions + outcome.schedules <= 1) {
    return null
  }
  const parts: string[] = []
  if (outcome.executions > 0) {
    parts.push(resourcePhrase(outcome.executions, 'exécution', 'exécutions'))
  }
  if (outcome.schedules > 0) {
    parts.push(resourcePhrase(outcome.schedules, 'planification', 'planifications'))
  }
  return `Cette validation créera ${parts.join(' et ')}.`
}
