import { combineCivilDateTimeToIso, splitIsoToCivil } from '@/lib/business-timezone'
import type { ActionPlanExecutionDetail, PatchedActionPlanExecutionUpdateRequest } from '../types'

/** Minimal PATCH: keep the start, tasks, assignees and validation policy intact. */
export function executionDeadlineChange(
  execution: Pick<
    ActionPlanExecutionDetail,
    'permission_hints' | 'use_shared_chronology' | 'start_at' | 'end_at' | 'all_day' | 'updated_at'
  >,
  date: string,
  timeZone: string,
): PatchedActionPlanExecutionUpdateRequest {
  if (!execution.permission_hints?.can_update)
    throw new Error('Vous ne pouvez pas modifier ce plan.')
  if (!execution.use_shared_chronology)
    throw new Error('Ce plan a des échéances individuelles. Modifiez-les depuis sa fiche.')
  if (!execution.start_at) throw new Error('Définissez d’abord le début du plan depuis sa fiche.')
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) throw new Error('Date invalide.')
  const time = execution.all_day
    ? '23:59'
    : splitIsoToCivil(execution.end_at ?? execution.start_at, timeZone).time
  const endAt = combineCivilDateTimeToIso(date, time, timeZone)
  if (
    !endAt ||
    splitIsoToCivil(endAt, timeZone).date !== date ||
    Date.parse(endAt) <= Date.parse(execution.start_at)
  ) {
    throw new Error('L’échéance doit être après le début du plan.')
  }
  return { expected_updated_at: execution.updated_at, end_at: endAt }
}
