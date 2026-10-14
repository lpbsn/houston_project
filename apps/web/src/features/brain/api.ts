import { apiClient, fetchWithAuthRetry, withAuthRetry } from '@/api/client'
import type { components } from '@/api/generated/types'
import { parseStandardApiError } from '@/lib/api-errors'

export type BrainReporting = components['schemas']['BrainReportingResponse']
export type BrainReportingList = components['schemas']['BrainReportingList']
export type BrainAnalysisSummary = components['schemas']['BrainAnalysisSummary']
export type BrainAnalysisList = components['schemas']['BrainAnalysisList']
export type BrainAnalysisDetail = components['schemas']['BrainAnalysisDetail']
export type BrainWork = components['schemas']['BrainWork']
export type BrainActiveWork = components['schemas']['BrainActiveWork']
export type BrainLaunchResponse = components['schemas']['BrainLaunchResponse']
export type BrainFollowUpResponse = components['schemas']['BrainFollowUpResponse']
export type BrainSuggestion = components['schemas']['BrainSuggestion']
export type BrainSuggestionConvertResponse = components['schemas']['BrainSuggestionConvertResponse']
export type BrainObjective = components['schemas']['BrainObjective']
export type BrainObjectiveList = components['schemas']['BrainObjectiveList']
export type BrainMechanism = components['schemas']['BrainMechanism']
export type BrainSourcePage = components['schemas']['BrainSourcePage']
export type BrainPlatformMechanism = components['schemas']['BrainPlatformMechanism']
export type BrainPlatformMechanismList = components['schemas']['BrainPlatformMechanismList']
export type BrainKnowledgeVersion = components['schemas']['BrainKnowledgeVersion']
export type BrainKnowledgeVersionList = components['schemas']['BrainKnowledgeVersionList']
export type BrainFollowUpPurpose = components['schemas']['PurposeEnum']

export class BrainApiError extends Error {
  status: number
  detail: string
  code: string | null

  constructor(options: { status: number; detail: string; code?: string | null }) {
    super(options.detail)
    this.name = 'BrainApiError'
    this.status = options.status
    this.detail = options.detail
    this.code = options.code ?? null
  }
}

export function isBrainAccessLoss(error: unknown): boolean {
  return error instanceof BrainApiError && (error.status === 403 || error.status === 404)
}

function authHeaders(accessToken: string | null) {
  return accessToken ? { Authorization: `Bearer ${accessToken}` } : undefined
}

function toBrainError(response: Response, payload: unknown): BrainApiError {
  const parsed = parseStandardApiError(response, payload)
  return new BrainApiError(parsed)
}

async function execute<T>(
  request: (accessToken: string | null) => Promise<{
    data?: T
    error?: unknown
    response: Response
  }>,
): Promise<T> {
  const result = await withAuthRetry(request)
  if (result.error || result.data === undefined) {
    throw toBrainError(result.response, result.error)
  }
  return result.data
}

export const brainQueryKeys = {
  reportings: (establishmentId: string) => ['brain', establishmentId, 'reportings'] as const,
  analyses: (establishmentId: string) => ['brain', establishmentId, 'analyses'] as const,
  analysis: (establishmentId: string, analysisId: string) =>
    ['brain', establishmentId, 'analysis', analysisId] as const,
  work: (establishmentId: string) => ['brain', establishmentId, 'work'] as const,
  sources: (establishmentId: string, analysisId: string) =>
    ['brain', establishmentId, 'sources', analysisId] as const,
  objectives: (establishmentId: string) => ['brain', establishmentId, 'objectives'] as const,
  platformMechanisms: ['brain', 'platform', 'mechanisms'] as const,
  platformVersions: ['brain', 'platform', 'versions'] as const,
}

export async function uploadBrainReporting(
  establishmentId: string,
  file: File,
): Promise<BrainReporting> {
  const body = new FormData()
  body.append('file', file)
  const response = await fetchWithAuthRetry(
    `/api/v1/establishments/${establishmentId}/brain/reportings/`,
    { method: 'POST', body },
  )
  const payload: unknown = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw toBrainError(response, payload)
  }
  return payload as BrainReporting
}

export function listBrainReportings(establishmentId: string, cursor?: string) {
  return execute<BrainReportingList>((accessToken) =>
    apiClient.GET('/api/v1/establishments/{establishment_id}/brain/reportings/', {
      params: {
        path: { establishment_id: establishmentId },
        query: cursor ? { cursor } : undefined,
      },
      headers: authHeaders(accessToken),
    }),
  )
}

export function confirmBrainPeriod(
  establishmentId: string,
  reportingId: string,
  period: { period_start: string; period_end: string },
) {
  return execute<BrainReporting>((accessToken) =>
    apiClient.POST(
      '/api/v1/establishments/{establishment_id}/brain/reportings/{reporting_id}/period/',
      {
        params: {
          path: { establishment_id: establishmentId, reporting_id: reportingId },
        },
        body: period,
        headers: authHeaders(accessToken),
      },
    ),
  )
}

export function listBrainAnalyses(establishmentId: string, cursor?: string) {
  return execute<BrainAnalysisList>((accessToken) =>
    apiClient.GET('/api/v1/establishments/{establishment_id}/brain/analyses/', {
      params: {
        path: { establishment_id: establishmentId },
        query: cursor ? { cursor } : undefined,
      },
      headers: authHeaders(accessToken),
    }),
  )
}

export function fetchBrainAnalysis(establishmentId: string, analysisId: string) {
  return execute<BrainAnalysisDetail>((accessToken) =>
    apiClient.GET('/api/v1/establishments/{establishment_id}/brain/analyses/{analysis_id}/', {
      params: {
        path: { establishment_id: establishmentId, analysis_id: analysisId },
      },
      headers: authHeaders(accessToken),
    }),
  )
}

export function fetchActiveBrainWork(establishmentId: string) {
  return execute<BrainActiveWork>((accessToken) =>
    apiClient.GET('/api/v1/establishments/{establishment_id}/brain/work/', {
      params: { path: { establishment_id: establishmentId } },
      headers: authHeaders(accessToken),
    }),
  )
}

export function launchBrainAnalysis(
  establishmentId: string,
  body: { reporting_id: string; idempotency_key: string },
) {
  return execute<BrainLaunchResponse>((accessToken) =>
    apiClient.POST('/api/v1/establishments/{establishment_id}/brain/analyses/', {
      params: { path: { establishment_id: establishmentId } },
      body,
      headers: authHeaders(accessToken),
    }),
  )
}

export function cancelBrainAnalysis(establishmentId: string, analysisId: string) {
  return execute<components['schemas']['BrainCancelResponse']>((accessToken) =>
    apiClient.POST(
      '/api/v1/establishments/{establishment_id}/brain/analyses/{analysis_id}/cancel/',
      {
        params: {
          path: { establishment_id: establishmentId, analysis_id: analysisId },
        },
        headers: authHeaders(accessToken),
      },
    ),
  )
}

export function listBrainSources(establishmentId: string, analysisId: string, cursor?: string) {
  return execute<BrainSourcePage>((accessToken) =>
    apiClient.GET(
      '/api/v1/establishments/{establishment_id}/brain/analyses/{analysis_id}/sources/',
      {
        params: {
          path: { establishment_id: establishmentId, analysis_id: analysisId },
          query: cursor ? { cursor } : undefined,
        },
        headers: authHeaders(accessToken),
      },
    ),
  )
}

export function createBrainFollowUp(
  establishmentId: string,
  analysisId: string,
  body: {
    request_id: string
    body: string
    purpose: BrainFollowUpPurpose
    cited_item_ids?: string[]
  },
) {
  return execute<BrainFollowUpResponse>((accessToken) =>
    apiClient.POST(
      '/api/v1/establishments/{establishment_id}/brain/analyses/{analysis_id}/messages/',
      {
        params: {
          path: { establishment_id: establishmentId, analysis_id: analysisId },
        },
        body,
        headers: authHeaders(accessToken),
      },
    ),
  )
}

export function cancelBrainFollowUp(establishmentId: string, messageId: string) {
  return execute<components['schemas']['BrainCancelResponse']>((accessToken) =>
    apiClient.POST('/api/v1/establishments/{establishment_id}/brain/messages/{message_id}/cancel/', {
      params: { path: { establishment_id: establishmentId, message_id: messageId } },
      headers: authHeaders(accessToken),
    }),
  )
}

export function reviseBrainSuggestion(
  establishmentId: string,
  suggestionId: string,
  body: components['schemas']['BrainSuggestionRevisionRequest'],
) {
  return execute<BrainSuggestion>((accessToken) =>
    apiClient.POST(
      '/api/v1/establishments/{establishment_id}/brain/suggestions/{suggestion_id}/revisions/',
      {
        params: {
          path: { establishment_id: establishmentId, suggestion_id: suggestionId },
        },
        body,
        headers: authHeaders(accessToken),
      },
    ),
  )
}

export function convertBrainSuggestion(
  establishmentId: string,
  suggestionId: string,
  expectedRevisionId: string,
) {
  return execute<BrainSuggestionConvertResponse>((accessToken) =>
    apiClient.POST(
      '/api/v1/establishments/{establishment_id}/brain/suggestions/{suggestion_id}/convert/',
      {
        params: {
          path: { establishment_id: establishmentId, suggestion_id: suggestionId },
        },
        body: { expected_revision_id: expectedRevisionId },
        headers: authHeaders(accessToken),
      },
    ),
  )
}

export function listBrainObjectives(establishmentId: string, cursor?: string) {
  return execute<BrainObjectiveList>((accessToken) =>
    apiClient.GET('/api/v1/establishments/{establishment_id}/brain/objectives/', {
      params: {
        path: { establishment_id: establishmentId },
        query: cursor ? { cursor } : undefined,
      },
      headers: authHeaders(accessToken),
    }),
  )
}

export function decideBrainObjective(
  establishmentId: string,
  objectiveId: string,
  body: components['schemas']['BrainObjectiveDecisionRequest'],
) {
  return execute<BrainObjective>((accessToken) =>
    apiClient.POST(
      '/api/v1/establishments/{establishment_id}/brain/objectives/{objective_id}/decisions/',
      {
        params: {
          path: { establishment_id: establishmentId, objective_id: objectiveId },
        },
        body,
        headers: authHeaders(accessToken),
      },
    ),
  )
}

export function reviseBrainMechanism(
  establishmentId: string,
  candidateId: string,
  body: components['schemas']['BrainMechanismRevisionRequest'],
) {
  return execute<components['schemas']['BrainPlatformRepresentation']>((accessToken) =>
    apiClient.POST(
      '/api/v1/establishments/{establishment_id}/brain/mechanisms/{candidate_id}/representation/',
      {
        params: {
          path: { establishment_id: establishmentId, candidate_id: candidateId },
        },
        body,
        headers: authHeaders(accessToken),
      },
    ),
  )
}

export function listPlatformMechanisms() {
  return execute<BrainPlatformMechanismList>((accessToken) =>
    apiClient.GET('/api/v1/platform/brain/mechanisms/', {
      headers: authHeaders(accessToken),
    }),
  )
}

export function decidePlatformMechanism(candidateId: string, decision: 'approve' | 'reject') {
  return execute<BrainPlatformMechanism>((accessToken) =>
    apiClient.POST('/api/v1/platform/brain/mechanisms/{candidate_id}/decision/', {
      params: { path: { candidate_id: candidateId } },
      body: { decision },
      headers: authHeaders(accessToken),
    }),
  )
}

export function listPlatformKnowledgeVersions() {
  return execute<BrainKnowledgeVersionList>((accessToken) =>
    apiClient.GET('/api/v1/platform/brain/knowledge/versions/', {
      headers: authHeaders(accessToken),
    }),
  )
}

export function activatePlatformKnowledgeVersion(versionId: string) {
  return execute<BrainKnowledgeVersion>((accessToken) =>
    apiClient.POST('/api/v1/platform/brain/knowledge/versions/{version_id}/activate/', {
      params: { path: { version_id: versionId } },
      headers: authHeaders(accessToken),
    }),
  )
}
