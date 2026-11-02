import { resolveActionPlanErrorMessage } from './action-plan-errors'
import type { ActionPlanExecutionDetail } from '../types'

export const DUPLICATE_EXECUTION_LOAD_ERROR = 'Impossible de charger le plan à dupliquer.'
export const EDIT_EXECUTION_RELOAD_ERROR = 'Ce plan a changé. Le rechargement a échoué.'
export const EDIT_EXECUTION_RELOADED_MESSAGE = 'Ce plan a changé. Les données ont été rechargées.'

type ExecutionDetailRefetch = () => Promise<{
  data?: ActionPlanExecutionDetail
  error?: unknown
}>

export type ExecutionDetailReload =
  | { ok: true; execution: ActionPlanExecutionDetail }
  | { ok: false; message: string }

export function executionDetailLoadMessage(error: unknown, fallback: string): string {
  return resolveActionPlanErrorMessage(error, fallback)
}

/** Shared reload and error text for the in-place editor and the duplication form. */
export async function reloadExecutionDetail(
  refetch: ExecutionDetailRefetch,
  fallback: string,
): Promise<ExecutionDetailReload> {
  try {
    const result = await refetch()
    if (result.data) return { ok: true, execution: result.data }
    return { ok: false, message: executionDetailLoadMessage(result.error, fallback) }
  } catch (error) {
    return { ok: false, message: executionDetailLoadMessage(error, fallback) }
  }
}
