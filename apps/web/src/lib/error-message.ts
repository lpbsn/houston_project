export function toErrorMessage(error: unknown, fallback = 'Une erreur est survenue.'): string {
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
  if (error instanceof ApiErrorClass) {
    const detail =
      'detail' in error && typeof (error as { detail?: unknown }).detail === 'string'
        ? (error as { detail: string }).detail
        : null
    return detail ?? error.message ?? fallback
  }

  return toErrorMessage(error, fallback)
}
