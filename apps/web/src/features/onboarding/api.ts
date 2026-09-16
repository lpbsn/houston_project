import { apiClient, withAuthRetry } from '@/api/client'

import type {
  ActivationBlocker,
  OnboardingSessionCreateRequest,
  OnboardingSessionCreateResponse,
  OnboardingSessionResponse,
  CatalogActivitySubjectSuggestion,
  CatalogBusinessUnitSuggestion,
  OnboardingCompleteResponse,
  OnboardingDraftResponse,
} from './types'
import type { OnboardingDraftPayload } from './lib/onboarding-draft-payload'

export const onboardingQueryKeys = {
  all: ['onboarding'] as const,
  sessions: () => ['onboarding', 'sessions'] as const,
  session: (sessionId: string) => ['onboarding', 'sessions', sessionId] as const,
  draft: (sessionId: string) =>
    ['onboarding', 'sessions', sessionId, 'draft'] as const,
  catalogBusinessUnits: (query: string) =>
    ['onboarding', 'catalog', 'business-units', query] as const,
  catalogActivitySubjects: (businessUnitKey: string, query: string) =>
    ['onboarding', 'catalog', 'activity-subjects', businessUnitKey, query] as const,
}

export class OnboardingApiError extends Error {
  status: number
  detail: string
  code: string | null
  blockers: ActivationBlocker[]
  payload: unknown

  constructor(options: {
    status: number
    detail: string
    code?: string | null
    blockers?: ActivationBlocker[]
    payload?: unknown
  }) {
    super(options.detail)
    this.name = 'OnboardingApiError'
    this.status = options.status
    this.detail = options.detail
    this.code = options.code ?? null
    this.blockers = options.blockers ?? []
    this.payload = options.payload
  }
}

function getAuthHeaders(accessToken: string | null) {
  return accessToken
    ? {
        Authorization: `Bearer ${accessToken}`,
      }
    : undefined
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function getDetail(payload: unknown) {
  if (!isRecord(payload) || typeof payload.detail !== 'string') {
    return null
  }

  return payload.detail
}

function getOnboardingCode(payload: unknown) {
  if (!isRecord(payload) || typeof payload.code !== 'string') {
    return null
  }

  return payload.code
}

function getActivationBlockers(payload: unknown) {
  if (!isRecord(payload) || !Array.isArray(payload.blockers)) {
    return []
  }

  return payload.blockers.filter(
    (blocker): blocker is ActivationBlocker =>
      isRecord(blocker) &&
      typeof blocker.code === 'string' &&
      typeof blocker.message === 'string',
  )
}

function buildOnboardingError(response: Response, error: unknown, fallbackDetail: string) {
  return new OnboardingApiError({
    status: response.status,
    detail: getDetail(error) ?? fallbackDetail,
    code: getOnboardingCode(error),
    blockers: getActivationBlockers(error),
    payload: error,
  })
}

export async function startOnboardingSession(input: OnboardingSessionCreateRequest) {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST('/api/v1/onboarding-sessions/', {
        body: input,
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )

  if (result.error || !result.data) {
    throw buildOnboardingError(
      result.response,
      result.error,
      'Onboarding session could not be started.',
    )
  }

  return result.data as OnboardingSessionCreateResponse
}

export async function getOnboardingSession(sessionId: string) {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.GET('/api/v1/onboarding-sessions/{session_id}/', {
        params: {
          path: { session_id: sessionId },
        },
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )

  if (result.error || !result.data) {
    throw buildOnboardingError(
      result.response,
      result.error,
      'Onboarding session could not be loaded.',
    )
  }

  return result.data as OnboardingSessionResponse
}

export async function suggestBusinessUnits(
  query: string,
  options?: { limit?: number },
) {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.GET('/api/v1/catalog/business-units/suggest/', {
        params: {
          query: {
            q: query,
            limit: options?.limit,
          },
        },
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )

  if (result.error || !result.data) {
    throw buildOnboardingError(
      result.response,
      result.error,
      'Les suggestions de pôles n’ont pas pu être chargées.',
    )
  }

  return result.data as CatalogBusinessUnitSuggestion[]
}

export async function getOnboardingDraft(sessionId: string) {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.GET('/api/v1/onboarding-sessions/{session_id}/draft/', {
        params: {
          path: { session_id: sessionId },
        },
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )

  if (result.error || !result.data) {
    throw buildOnboardingError(
      result.response,
      result.error,
      'Le brouillon d’onboarding n’a pas pu être chargé.',
    )
  }

  return result.data as OnboardingDraftResponse
}

export async function putOnboardingDraft(
  sessionId: string,
  payload: OnboardingDraftPayload,
) {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.PUT('/api/v1/onboarding-sessions/{session_id}/draft/', {
        params: {
          path: { session_id: sessionId },
        },
        body: { payload },
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )

  if (result.error || !result.data) {
    throw buildOnboardingError(
      result.response,
      result.error,
      'Le brouillon d’onboarding n’a pas pu être enregistré.',
    )
  }

  return result.data as OnboardingDraftResponse
}

export async function completeOnboardingSession(sessionId: string) {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST('/api/v1/onboarding-sessions/{session_id}/complete/', {
        params: {
          path: { session_id: sessionId },
        },
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )

  if (result.error || !result.data) {
    throw buildOnboardingError(
      result.response,
      result.error,
      'L’onboarding n’a pas pu être terminé.',
    )
  }

  return result.data as OnboardingCompleteResponse
}

export async function suggestActivitySubjects(
  businessUnitKey: string,
  query: string,
  options?: { limit?: number },
) {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.GET('/api/v1/catalog/activity-subjects/suggest/', {
        params: {
          query: {
            business_unit_key: businessUnitKey,
            q: query,
            limit: options?.limit ?? 20,
          },
        },
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )

  if (result.error || !result.data) {
    throw buildOnboardingError(
      result.response,
      result.error,
      'Les suggestions de sujets n’ont pas pu être chargées.',
    )
  }

  return result.data as CatalogActivitySubjectSuggestion[]
}

