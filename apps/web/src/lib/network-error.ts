export const NETWORK_FAILURE_MESSAGE =
  'Connexion indisponible. Vérifiez votre réseau et réessayez.'

export const OFFLINE_BANNER_MESSAGE = 'Hors ligne — vérifiez votre connexion réseau.'

function hasHttpStatus(error: unknown): error is { status: number } {
  return (
    typeof error === 'object' &&
    error !== null &&
    'status' in error &&
    typeof (error as { status: unknown }).status === 'number' &&
    (error as { status: number }).status > 0
  )
}

function isFetchTypeError(error: TypeError): boolean {
  const message = error.message.toLowerCase()
  return (
    message.includes('failed to fetch') ||
    message.includes('networkerror') ||
    message.includes('load failed')
  )
}

export function isNetworkFailure(error: unknown): boolean {
  if (hasHttpStatus(error)) {
    return false
  }

  if (error instanceof TypeError && isFetchTypeError(error)) {
    return true
  }

  if (error instanceof DOMException && error.name === 'NetworkError') {
    return true
  }

  return false
}
