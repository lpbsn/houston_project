import { apiClient, withAuthRetry } from '@/api/client'
import type { components } from '@/api/generated/types'
import { ensureCsrfToken } from '@/features/auth/csrf'
import {
  businessUnitTreeQueryKey,
  fetchBusinessUnitTree,
  type BusinessUnitTreeResponse,
} from '@/features/auth/api'

export { businessUnitTreeQueryKey, fetchBusinessUnitTree }
export type { BusinessUnitTreeResponse }

export type BusinessUnitTreeItem = BusinessUnitTreeResponse['business_units'][number]
export type ActivitySubjectTreeItem = BusinessUnitTreeItem['activity_subjects'][number]

type RuntimeBusinessUnitCreateRequest = components['schemas']['RuntimeBusinessUnitCreateRequest']
type RuntimeBusinessUnitUpdateRequest =
  components['schemas']['PatchedRuntimeBusinessUnitUpdateRequest']
type RuntimeActivitySubjectCreateRequest =
  components['schemas']['RuntimeActivitySubjectCreateRequest']

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

function getRuntimeConfigHeaders(accessToken: string | null, csrfToken: string) {
  return {
    'X-CSRFToken': csrfToken,
    ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
  }
}

function throwRuntimeConfigError(
  response: Response,
  error: unknown,
  fallback: string,
): never {
  const body = typeof error === 'object' && error !== null ? error : {}
  const detail =
    'detail' in body && typeof body.detail === 'string' ? body.detail : fallback
  const code = 'code' in body && typeof body.code === 'string' ? body.code : null
  throw new RuntimeConfigApiError(detail, response.status, code)
}

function assertRuntimeConfigData<T>(
  result: {
    response: Response
    data?: T
    error?: unknown
  },
  fallback: string,
): T {
  if (result.response.ok && result.data) {
    return result.data
  }

  throwRuntimeConfigError(result.response, result.error, fallback)
}

async function withRuntimeConfigMutation<T>(
  fallbackError: string,
  execute: (
    accessToken: string | null,
    csrfToken: string,
  ) => Promise<{ response: Response; data?: T; error?: unknown }>,
): Promise<T> {
  const csrfToken = await ensureCsrfToken()
  const result = await withAuthRetry(
    (accessToken) => execute(accessToken, csrfToken),
    { refreshable: true },
  )

  return assertRuntimeConfigData(result, fallbackError)
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
  return withRuntimeConfigMutation('Le pôle n’a pas pu être créé.', (accessToken, csrfToken) =>
    apiClient.POST('/api/v1/establishments/{establishment_id}/business-units/', {
      params: {
        path: { establishment_id: establishmentId },
      },
      body: input as RuntimeBusinessUnitCreateRequest,
      credentials: 'include',
      headers: getRuntimeConfigHeaders(accessToken, csrfToken),
    }),
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
  return withRuntimeConfigMutation(
    'Le pôle n’a pas pu être mis à jour.',
    (accessToken, csrfToken) =>
      apiClient.PATCH(
        '/api/v1/establishments/{establishment_id}/business-units/{business_unit_id}/',
        {
          params: {
            path: {
              establishment_id: establishmentId,
              business_unit_id: businessUnitId,
            },
          },
          body: input as RuntimeBusinessUnitUpdateRequest,
          credentials: 'include',
          headers: getRuntimeConfigHeaders(accessToken, csrfToken),
        },
      ),
  )
}

export async function deactivateRuntimeBusinessUnit(
  establishmentId: string,
  businessUnitId: string,
): Promise<BusinessUnitTreeItem> {
  return withRuntimeConfigMutation('Le pôle n’a pas pu être retiré.', (accessToken, csrfToken) =>
    apiClient.POST(
      '/api/v1/establishments/{establishment_id}/business-units/{business_unit_id}/deactivate/',
      {
        params: {
          path: {
            establishment_id: establishmentId,
            business_unit_id: businessUnitId,
          },
        },
        credentials: 'include',
        headers: getRuntimeConfigHeaders(accessToken, csrfToken),
      },
    ),
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
  return withRuntimeConfigMutation('Le sujet n’a pas pu être créé.', (accessToken, csrfToken) =>
    apiClient.POST(
      '/api/v1/establishments/{establishment_id}/business-units/{business_unit_id}/activity-subjects/',
      {
        params: {
          path: {
            establishment_id: establishmentId,
            business_unit_id: businessUnitId,
          },
        },
        body: input as RuntimeActivitySubjectCreateRequest,
        credentials: 'include',
        headers: getRuntimeConfigHeaders(accessToken, csrfToken),
      },
    ),
  )
}

export async function deactivateRuntimeActivitySubject(
  establishmentId: string,
  activitySubjectId: string,
): Promise<ActivitySubjectTreeItem> {
  return withRuntimeConfigMutation('Le sujet n’a pas pu être retiré.', (accessToken, csrfToken) =>
    apiClient.POST(
      '/api/v1/establishments/{establishment_id}/activity-subjects/{activity_subject_id}/deactivate/',
      {
        params: {
          path: {
            establishment_id: establishmentId,
            activity_subject_id: activitySubjectId,
          },
        },
        credentials: 'include',
        headers: getRuntimeConfigHeaders(accessToken, csrfToken),
      },
    ),
  )
}
