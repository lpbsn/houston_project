import { withAuthRetry } from '@/api/client'
import { ensureCsrfToken } from '@/features/auth/csrf'
import { businessUnitTreeQueryKey, type BusinessUnitTreeResponse } from '@/features/auth/api'
import { getAccessToken } from '@/features/auth/session'

export { businessUnitTreeQueryKey }
export type { BusinessUnitTreeResponse }

export type BusinessUnitTreeItem = BusinessUnitTreeResponse['business_units'][number]
export type ActivitySubjectTreeItem = BusinessUnitTreeItem['activity_subjects'][number]

export type RuntimeConfigApiErrorPayload = {
  code?: string
  detail?: string
}

export class RuntimeConfigApiError extends Error {
  status: number
  code: string | null

  constructor(message: string, status: number, code: string | null = null) {
    super(message)
    this.name = 'RuntimeConfigApiError'
    this.status = status
    this.code = code
  }
}

async function parseRuntimeConfigError(response: Response, fallback: string): Promise<never> {
  try {
    const payload = (await response.json()) as RuntimeConfigApiErrorPayload
    throw new RuntimeConfigApiError(
      payload?.detail ?? fallback,
      response.status,
      payload?.code ?? null,
    )
  } catch (error) {
    if (error instanceof RuntimeConfigApiError) {
      throw error
    }

    throw new RuntimeConfigApiError(fallback, response.status)
  }
}

async function runtimeConfigRequest<T>(
  path: string,
  init: RequestInit,
  fallbackError: string,
): Promise<T> {
  const csrfToken = await ensureCsrfToken()

  const response = await fetch(path, {
    ...init,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(getAccessToken() ? { Authorization: `Bearer ${getAccessToken()}` } : {}),
      'X-CSRFToken': csrfToken,
      ...(init.headers ?? {}),
    },
  })

  if (!response.ok) {
    await parseRuntimeConfigError(response, fallbackError)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return response.json() as Promise<T>
}

export async function createRuntimeBusinessUnit(
  establishmentId: string,
  input: {
    label: string
    description?: string
    unit_type?: string
    catalog_key?: string | null
  },
): Promise<BusinessUnitTreeItem> {
  return runtimeConfigRequest(
    `/api/v1/establishments/${establishmentId}/business-units/`,
    {
      method: 'POST',
      body: JSON.stringify(input),
    },
    'Le pôle n’a pas pu être créé.',
  )
}

export async function updateRuntimeBusinessUnit(
  establishmentId: string,
  businessUnitId: string,
  input: {
    label?: string
    description?: string
    unit_type?: string
  },
): Promise<BusinessUnitTreeItem> {
  return runtimeConfigRequest(
    `/api/v1/establishments/${establishmentId}/business-units/${businessUnitId}/`,
    {
      method: 'PATCH',
      body: JSON.stringify(input),
    },
    'Le pôle n’a pas pu être mis à jour.',
  )
}

export async function deactivateRuntimeBusinessUnit(
  establishmentId: string,
  businessUnitId: string,
): Promise<BusinessUnitTreeItem> {
  return runtimeConfigRequest(
    `/api/v1/establishments/${establishmentId}/business-units/${businessUnitId}/deactivate/`,
    {
      method: 'POST',
      body: JSON.stringify({}),
    },
    'Le pôle n’a pas pu être retiré.',
  )
}

export async function createRuntimeActivitySubject(
  establishmentId: string,
  businessUnitId: string,
  input: {
    label: string
    description?: string
    catalog_key?: string | null
  },
): Promise<ActivitySubjectTreeItem> {
  return runtimeConfigRequest(
    `/api/v1/establishments/${establishmentId}/business-units/${businessUnitId}/activity-subjects/`,
    {
      method: 'POST',
      body: JSON.stringify(input),
    },
    'Le sujet n’a pas pu être créé.',
  )
}

export async function deactivateRuntimeActivitySubject(
  establishmentId: string,
  activitySubjectId: string,
): Promise<ActivitySubjectTreeItem> {
  return runtimeConfigRequest(
    `/api/v1/establishments/${establishmentId}/activity-subjects/${activitySubjectId}/deactivate/`,
    {
      method: 'POST',
      body: JSON.stringify({}),
    },
    'Le sujet n’a pas pu être retiré.',
  )
}

export async function fetchBusinessUnitTreeWithAuth(establishmentId: string) {
  const csrfToken = await ensureCsrfToken()
  const result = await withAuthRetry(
    (accessToken) =>
      fetch(`/api/v1/establishments/${establishmentId}/business-units/`, {
        credentials: 'include',
        headers: {
          ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
          'X-CSRFToken': csrfToken,
        },
      }).then(async (response) => ({ response, data: response.ok ? await response.json() : null })),
    { refreshable: true },
  )

  if (!result.response.ok || !result.data) {
    throw new RuntimeConfigApiError(
      'La configuration opérationnelle n’a pas pu être chargée.',
      result.response.status,
    )
  }

  return result.data as BusinessUnitTreeResponse
}
