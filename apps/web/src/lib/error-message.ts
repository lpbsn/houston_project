import { isNetworkFailure, NETWORK_FAILURE_MESSAGE } from '@/lib/network-error'

export function toErrorMessage(error: unknown, fallback = 'Une erreur est survenue.'): string {
  if (isNetworkFailure(error)) {
    return NETWORK_FAILURE_MESSAGE
  }

  if (error instanceof Error && error.message) {
    return error.message
  }

  return fallback
}

export function resolveApiErrorMessage(
  error: unknown,
  ApiErrorClass: new (...args: never[]) => Error,
  fallback: string,
): string {
  if (isNetworkFailure(error)) {
    return NETWORK_FAILURE_MESSAGE
  }

  if (error instanceof ApiErrorClass) {
    const detail =
      'detail' in error && typeof (error as { detail?: unknown }).detail === 'string'
        ? (error as { detail: string }).detail
        : null
    return detail ?? error.message ?? fallback
  }

  return toErrorMessage(error, fallback)
}
