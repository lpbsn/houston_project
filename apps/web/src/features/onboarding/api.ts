import { apiClient, withAuthRetry } from '@/api/client'

import type {
  AIOnboardingGenerateRequest,
  ActivationBlocker,
  ActivationResponse,
  ActivationSummaryResponse,
  ActivityDescriptionUpdateResponse,
  DetailResponse,
  DirectorInvitationRequest,
  DirectorInvitationResponse,
  MarkReadyResponse,
  OnboardingErrorResponse,
  OnboardingProposalErrorResponse,
  OnboardingProposalResponse,
  OnboardingSessionCreateRequest,
  OnboardingSessionCreateResponse,
  OnboardingSessionResponse,
  ProposalCommandResponse,
  ProposalItemMutationRequest,
  ProposalSectionDecisionRequest,
  ProposalValidationErrorItem,
  RuntimeConfigResponse,
  SubmitActivityDescriptionRequest,
  CatalogActivitySubjectSuggestion,
  CatalogBusinessUnitSuggestion,
  OnboardingProposalCreateRequest,
  OnboardingProposalUpdateRequest,
} from './types'

export const onboardingQueryKeys = {
  all: ['onboarding'] as const,
  sessions: () => ['onboarding', 'sessions'] as const,
  session: (sessionId: string) => ['onboarding', 'sessions', sessionId] as const,
  proposals: (sessionId: string) =>
    ['onboarding', 'sessions', sessionId, 'proposals'] as const,
  proposal: (sessionId: string, proposalId: string) =>
    ['onboarding', 'sessions', sessionId, 'proposals', proposalId] as const,
  runtimeConfig: (sessionId: string) =>
    ['onboarding', 'sessions', sessionId, 'runtime-config'] as const,
  activationSummary: (sessionId: string) =>
    ['onboarding', 'sessions', sessionId, 'activation-summary'] as const,
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
  proposalErrors: ProposalValidationErrorItem[]
  payload: unknown

  constructor(options: {
    status: number
    detail: string
    code?: string | null
    blockers?: ActivationBlocker[]
    proposalErrors?: ProposalValidationErrorItem[]
    payload?: unknown
  }) {
    super(options.detail)
    this.name = 'OnboardingApiError'
    this.status = options.status
    this.detail = options.detail
    this.code = options.code ?? null
    this.blockers = options.blockers ?? []
    this.proposalErrors = options.proposalErrors ?? []
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

function getProposalValidationErrors(payload: unknown) {
  if (!isRecord(payload) || !Array.isArray(payload.errors)) {
    return []
  }

  return payload.errors.filter(
    (error): error is ProposalValidationErrorItem =>
      isRecord(error) && typeof error.code === 'string',
  )
}

function buildOnboardingError(response: Response, error: unknown, fallbackDetail: string) {
  return new OnboardingApiError({
    status: response.status,
    detail: getDetail(error) ?? fallbackDetail,
    code: getOnboardingCode(error),
    blockers: getActivationBlockers(error),
    proposalErrors: getProposalValidationErrors(error),
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

export async function inviteDirector(sessionId: string, input: DirectorInvitationRequest) {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST('/api/v1/onboarding-sessions/{session_id}/director-invitations/', {
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
      'Director invitation could not be sent.',
    )
  }

  return result.data as DirectorInvitationResponse
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

export async function activateOnboardingSession(sessionId: string) {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST('/api/v1/onboarding-sessions/{session_id}/activate/', {
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
      'Onboarding session could not be activated.',
    )
  }

  return result.data as ActivationResponse
}

export async function suggestBusinessUnits(query: string) {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.GET('/api/v1/catalog/business-units/suggest/', {
        params: {
          query: {
            q: query,
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

export async function createManualOnboardingProposal(
  sessionId: string,
  input: OnboardingProposalCreateRequest,
) {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST('/api/v1/onboarding-sessions/{session_id}/proposals/', {
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
      result.error as
        | DetailResponse
        | OnboardingProposalErrorResponse
        | undefined,
      'La proposition d’onboarding n’a pas pu être créée.',
    )
  }

  return result.data as ProposalCommandResponse
}

export async function updateManualOnboardingProposal(
  sessionId: string,
  proposalId: string,
  input: OnboardingProposalUpdateRequest,
) {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.PATCH('/api/v1/onboarding-sessions/{session_id}/proposals/{proposal_id}/', {
        params: {
          path: { session_id: sessionId, proposal_id: proposalId },
        },
        body: input,
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )

  if (result.error || !result.data) {
    throw buildOnboardingError(
      result.response,
      result.error as
        | DetailResponse
        | OnboardingProposalErrorResponse
        | undefined,
      'La proposition d’onboarding n’a pas pu être mise à jour.',
    )
  }

  return result.data as ProposalCommandResponse
}

export async function submitManualOnboardingProposal(sessionId: string, proposalId: string) {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST(
        '/api/v1/onboarding-sessions/{session_id}/proposals/{proposal_id}/submit/',
        {
          params: {
            path: { session_id: sessionId, proposal_id: proposalId },
          },
          headers: getAuthHeaders(accessToken),
        },
      ),
    { refreshable: true },
  )

  if (result.error || !result.data) {
    throw buildOnboardingError(
      result.response,
      result.error as
        | DetailResponse
        | OnboardingProposalErrorResponse
        | undefined,
      'La proposition d’onboarding n’a pas pu être validée.',
    )
  }

  return result.data as ProposalCommandResponse
}

export async function listOnboardingProposals(sessionId: string) {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.GET('/api/v1/onboarding-sessions/{session_id}/proposals/', {
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
      result.error as DetailResponse | undefined,
      'Onboarding proposals could not be loaded.',
    )
  }

  return result.data as OnboardingProposalResponse[]
}

export async function getOnboardingProposal(sessionId: string, proposalId: string) {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.GET('/api/v1/onboarding-sessions/{session_id}/proposals/{proposal_id}/', {
        params: {
          path: { session_id: sessionId, proposal_id: proposalId },
        },
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )

  if (result.error || !result.data) {
    throw buildOnboardingError(
      result.response,
      result.error as DetailResponse | undefined,
      'Onboarding proposal could not be loaded.',
    )
  }

  return result.data as OnboardingProposalResponse
}

export async function generateOnboardingProposal(
  sessionId: string,
  input: AIOnboardingGenerateRequest,
) {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST('/api/v1/onboarding-sessions/{session_id}/proposals/ai-generate/', {
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
      result.error as
        | DetailResponse
        | OnboardingProposalErrorResponse
        | undefined,
      'AI onboarding proposal could not be generated.',
    )
  }

  return result.data as ProposalCommandResponse
}

export async function decideProposalSection(
  sessionId: string,
  proposalId: string,
  section: string,
  input: ProposalSectionDecisionRequest,
) {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST(
        '/api/v1/onboarding-sessions/{session_id}/proposals/{proposal_id}/sections/{section}/decision/',
        {
          params: {
            path: { session_id: sessionId, proposal_id: proposalId, section },
          },
          body: input,
          headers: getAuthHeaders(accessToken),
        },
      ),
    { refreshable: true },
  )

  if (result.error || !result.data) {
    throw buildOnboardingError(
      result.response,
      result.error as
        | DetailResponse
        | OnboardingProposalErrorResponse
        | undefined,
      'Proposal section decision could not be saved.',
    )
  }

  return result.data as ProposalCommandResponse
}

export async function rejectOnboardingProposal(sessionId: string, proposalId: string) {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST('/api/v1/onboarding-sessions/{session_id}/proposals/{proposal_id}/reject/', {
        params: {
          path: { session_id: sessionId, proposal_id: proposalId },
        },
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )

  if (result.error || !result.data) {
    throw buildOnboardingError(
      result.response,
      result.error as
        | DetailResponse
        | OnboardingProposalErrorResponse
        | undefined,
      'Onboarding proposal could not be rejected.',
    )
  }

  return result.data as ProposalCommandResponse
}

export async function applyOnboardingProposal(sessionId: string, proposalId: string) {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST('/api/v1/onboarding-sessions/{session_id}/proposals/{proposal_id}/apply/', {
        params: {
          path: { session_id: sessionId, proposal_id: proposalId },
        },
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )

  if (result.error || !result.data) {
    throw buildOnboardingError(
      result.response,
      result.error as
        | DetailResponse
        | OnboardingProposalErrorResponse
        | undefined,
      'Onboarding proposal could not be applied.',
    )
  }

  return result.data as ProposalCommandResponse
}

export async function mutateOnboardingProposalItem(
  sessionId: string,
  proposalId: string,
  input: ProposalItemMutationRequest,
) {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST('/api/v1/onboarding-sessions/{session_id}/proposals/{proposal_id}/items/', {
        params: {
          path: { session_id: sessionId, proposal_id: proposalId },
        },
        body: input,
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )

  if (result.error || !result.data) {
    throw buildOnboardingError(
      result.response,
      result.error as
        | DetailResponse
        | OnboardingProposalErrorResponse
        | undefined,
      'Proposal item could not be updated.',
    )
  }

  return result.data as ProposalCommandResponse
}
