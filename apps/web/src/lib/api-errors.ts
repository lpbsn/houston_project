export type StandardApiErrorFields = {
  status: number
  detail: string
  code: string | null
}

export function parseStandardApiError(
  response: Response,
  payload: unknown,
  fallbackDetail = 'Une erreur est survenue.',
): StandardApiErrorFields {
  const body = typeof payload === 'object' && payload !== null ? payload : {}
  const detail =
    'detail' in body && typeof body.detail === 'string' ? body.detail : fallbackDetail
  const code = 'code' in body && typeof body.code === 'string' ? body.code : null

  return {
    status: response.status,
    detail,
    code,
  }
}
