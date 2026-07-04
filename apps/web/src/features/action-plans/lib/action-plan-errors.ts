import { ActionPlansApiError } from '../api'

export function resolveActionPlanErrorMessage(
  error: unknown,
  fallback: string,
): string {
  if (error instanceof ActionPlansApiError) {
    return error.detail || fallback
  }
  if (error instanceof Error && error.message) {
    return error.message
  }
  return fallback
}
