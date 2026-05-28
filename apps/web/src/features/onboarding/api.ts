import { apiClient, withAuthRetry } from '@/api/client'

import type {
  ActivationBlocker,
  ActivationSummaryResponse,
  ActivityDescriptionUpdateResponse,
  DetailResponse,
  MarkReadyResponse,
  OnboardingErrorResponse,
  OnboardingSessionCreateRequest,
  OnboardingSessionCreateResponse,
  OnboardingSessionResponse,
  RuntimeConfigResponse,
  SubmitActivityDescriptionRequest,
} from './types'

export const onboardingQueryKeys = {
  all: ['onboarding'] as const,
  sessions: () => ['onboarding', 'sessions'] as const,
  session: (sessionId: string) => ['onboarding', 'sessions', sessionId] as const,
  runtimeConfig: (sessionId: string) =>
    ['onboarding', 'sessions', sessionId, 'runtime-config'] as const,
  activationSummary: (sessionId: string) =>
    ['onboarding', 'sessions', sessionId, 'activation-summary'] as const,
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

export async function submitActivityDescription(
  sessionId: string,
  input: SubmitActivityDescriptionRequest,
) {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.PATCH('/api/v1/onboarding-sessions/{session_id}/description/', {
        params: {
          path: { session_id: sessionId },
        },
        body: input,
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )

  if (result.error || !result.data) {
    throw buildOnboardingError(
      result.response,
      result.error,
      'Activity description could not be saved.',
    )
  }

  return result.data as ActivityDescriptionUpdateResponse
}

export async function getRuntimeConfig(sessionId: string) {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.GET('/api/v1/onboarding-sessions/{session_id}/runtime-config/', {
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
      result.error as DetailResponse | OnboardingErrorResponse | undefined,
      'Runtime configuration could not be loaded.',
    )
  }

  return result.data as RuntimeConfigResponse
}

export async function getActivationSummary(sessionId: string) {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.GET('/api/v1/onboarding-sessions/{session_id}/activation-summary/', {
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
      result.error as DetailResponse | OnboardingErrorResponse | undefined,
      'Activation summary could not be loaded.',
    )
  }

  return result.data as ActivationSummaryResponse
}

export async function markReady(sessionId: string) {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST('/api/v1/onboarding-sessions/{session_id}/mark-ready/', {
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
      'Onboarding session could not be marked ready.',
    )
  }

  return result.data as MarkReadyResponse
}
