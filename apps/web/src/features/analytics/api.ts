import { apiClient, withAuthRetry } from '@/api/client'
import type { components } from '@/api/generated/types'
import { parseStandardApiError } from '@/lib/api-errors'

import type { AnalyticsUrlState } from './lib/analytics-url-state'

export type AnalyticsDashboardResponse =
  components['schemas']['AnalyticsDashboardResponse']
export type AnalyticsKPIResult = components['schemas']['AnalyticsKPIResult']
export type AnalyticsMetricComparison =
  components['schemas']['AnalyticsMetricComparison']
export type AnalyticsPatternListResponse =
  components['schemas']['AnalyticsPatternListResponse']
export type AnalyticsPatternListItem =
  components['schemas']['AnalyticsPatternListItem']
export type AnalyticsPatternFilterOptionsResponse =
  components['schemas']['AnalyticsPatternFilterOptionsResponse']
export type AnalyticsPatternDetailResponse =
  components['schemas']['AnalyticsPatternDetailResponse']
export type AnalyticsPatternSignalsResponse =
  components['schemas']['AnalyticsPatternSignalsResponse']
export type AnalyticsPatternSignalItem =
  components['schemas']['AnalyticsPatternSignalItem']
export type AnalyticsPatternIssueReportRequest =
  components['schemas']['AnalyticsPatternIssueReportRequest']
export type AnalyticsPatternIssueReportResponse =
  components['schemas']['AnalyticsPatternIssueReportResponse']

export const analyticsQueryKeys = {
  all: ['analytics'] as const,
  dashboard: (state: AnalyticsUrlState) =>
    [
      'analytics',
      'dashboard',
      {
        periodStart: state.periodStart,
        periodEnd: state.periodEnd,
        organizationId: state.organizationId,
      },
    ] as const,
  patterns: (state: AnalyticsUrlState, pageSize?: number) =>
    [
      'analytics',
      'patterns',
      {
        periodStart: state.periodStart,
        periodEnd: state.periodEnd,
        organizationId: state.organizationId,
        establishmentIds: state.establishmentIds,
        q: state.q,
        recurrence: state.recurrence,
        responsibleBusinessUnitIds: state.responsibleBusinessUnitIds,
        responsibleBusinessUnitUnassigned: state.responsibleBusinessUnitUnassigned,
        signalStatuses: state.signalStatuses,
        pageSize: pageSize ?? null,
      },
    ] as const,
  patternFilterOptions: (state: AnalyticsUrlState) =>
    [
      'analytics',
      'pattern-filter-options',
      {
        organizationId: state.organizationId,
        establishmentIds: state.establishmentIds,
      },
    ] as const,
  patternDetail: (patternId: string, state: AnalyticsUrlState) =>
    [
      'analytics',
      'pattern-detail',
      patternId,
      {
        periodStart: state.periodStart,
        periodEnd: state.periodEnd,
        organizationId: state.organizationId,
      },
    ] as const,
  patternSignals: (patternId: string, state: AnalyticsUrlState, pageSize?: number) =>
    [
      'analytics',
      'pattern-signals',
      patternId,
      {
        periodStart: state.periodStart,
        periodEnd: state.periodEnd,
        organizationId: state.organizationId,
        pageSize: pageSize ?? null,
      },
    ] as const,
  patternIssueReport: (patternId: string, signalId: string) =>
    ['analytics', 'pattern-issue-report', patternId, signalId] as const,
}

export class AnalyticsApiError extends Error {
  status: number
  detail: string
  code: string | null

  constructor(options: { status: number; detail: string; code?: string | null }) {
    super(options.detail)
    this.name = 'AnalyticsApiError'
    this.status = options.status
    this.detail = options.detail
    this.code = options.code ?? null
  }
}

function getAuthHeaders(accessToken: string | null) {
  return accessToken
    ? {
        Authorization: `Bearer ${accessToken}`,
      }
    : undefined
}

function parseError(response: Response, payload: unknown): AnalyticsApiError {
  const { status, detail, code } = parseStandardApiError(response, payload)
  return new AnalyticsApiError({ status, detail, code })
}

function assertAnalyticsData<T>(result: {
  response: Response
  data?: T
  error?: unknown
}): T {
  if (result.response.ok && result.data) {
    return result.data
  }

  throw parseError(result.response, result.error)
}

function buildDashboardQuery(state: AnalyticsUrlState) {
  return {
    period_start: state.periodStart,
    period_end: state.periodEnd,
    ...(state.organizationId ? { organization_id: state.organizationId } : {}),
  }
}

function buildPatternListQuery(
  state: AnalyticsUrlState,
  options: { cursor?: string; pageSize?: number } = {},
) {
  return {
    period_start: state.periodStart,
    period_end: state.periodEnd,
    ...(state.organizationId ? { organization_id: state.organizationId } : {}),
    ...(state.establishmentIds.length > 0
      ? { establishment_ids: state.establishmentIds.join(',') }
      : {}),
    ...(state.q.trim() ? { q: state.q.trim() } : {}),
    ...(state.recurrence !== 'all' ? { recurrence: state.recurrence } : {}),
    ...(state.responsibleBusinessUnitIds.length > 0
      ? { responsible_business_unit_ids: state.responsibleBusinessUnitIds.join(',') }
      : {}),
    ...(state.responsibleBusinessUnitUnassigned
      ? { responsible_business_unit_unassigned: true }
      : {}),
    ...(state.signalStatuses.length > 0
      ? { signal_statuses: state.signalStatuses.join(',') }
      : {}),
    ...(options.cursor ? { cursor: options.cursor } : {}),
    ...(options.pageSize ? { page_size: options.pageSize } : {}),
  }
}

function buildPatternFilterOptionsQuery(state: AnalyticsUrlState) {
  return {
    ...(state.organizationId ? { organization_id: state.organizationId } : {}),
    ...(state.establishmentIds.length > 0
      ? { establishment_ids: state.establishmentIds.join(',') }
      : {}),
  }
}

function buildPatternDetailQuery(state: AnalyticsUrlState) {
  return {
    period_start: state.periodStart,
    period_end: state.periodEnd,
    ...(state.organizationId ? { organization_id: state.organizationId } : {}),
  }
}

function buildPatternSignalsQuery(
  state: AnalyticsUrlState,
  options: { cursor?: string; pageSize?: number } = {},
) {
  return {
    period_start: state.periodStart,
    period_end: state.periodEnd,
    ...(state.organizationId ? { organization_id: state.organizationId } : {}),
    ...(options.cursor ? { cursor: options.cursor } : {}),
    ...(options.pageSize ? { page_size: options.pageSize } : {}),
  }
}

export async function fetchAnalyticsDashboard(
  state: AnalyticsUrlState,
): Promise<AnalyticsDashboardResponse> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.GET('/api/v1/analytics/dashboard/', {
        params: {
          query: buildDashboardQuery(state),
        },
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )

  return assertAnalyticsData<AnalyticsDashboardResponse>(result)
}

export async function fetchAnalyticsPatterns(
  state: AnalyticsUrlState,
  options: { cursor?: string; pageSize?: number } = {},
): Promise<AnalyticsPatternListResponse> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.GET('/api/v1/analytics/patterns/', {
        params: {
          query: buildPatternListQuery(state, options),
        },
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )

  return assertAnalyticsData<AnalyticsPatternListResponse>(result)
}

export async function fetchAnalyticsPatternFilterOptions(
  state: AnalyticsUrlState,
): Promise<AnalyticsPatternFilterOptionsResponse> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.GET('/api/v1/analytics/pattern-filter-options/', {
        params: {
          query: buildPatternFilterOptionsQuery(state),
        },
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )

  return assertAnalyticsData<AnalyticsPatternFilterOptionsResponse>(result)
}

export async function fetchAnalyticsPatternDetail(
  patternId: string,
  state: AnalyticsUrlState,
): Promise<AnalyticsPatternDetailResponse> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.GET('/api/v1/analytics/patterns/{pattern_id}/', {
        params: {
          path: { pattern_id: patternId },
          query: buildPatternDetailQuery(state),
        },
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )

  return assertAnalyticsData<AnalyticsPatternDetailResponse>(result)
}

export async function fetchAnalyticsPatternSignals(
  patternId: string,
  state: AnalyticsUrlState,
  options: { cursor?: string; pageSize?: number } = {},
): Promise<AnalyticsPatternSignalsResponse> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.GET('/api/v1/analytics/patterns/{pattern_id}/signals/', {
        params: {
          path: { pattern_id: patternId },
          query: buildPatternSignalsQuery(state, options),
        },
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )

  return assertAnalyticsData<AnalyticsPatternSignalsResponse>(result)
}

export async function reportAnalyticsPatternIssue(
  patternId: string,
  signalId: string,
  body: AnalyticsPatternIssueReportRequest,
): Promise<AnalyticsPatternIssueReportResponse> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST(
        '/api/v1/analytics/patterns/{pattern_id}/signals/{signal_id}/issue-report/',
        {
          params: {
            path: { pattern_id: patternId, signal_id: signalId },
          },
          body,
          headers: getAuthHeaders(accessToken),
        },
      ),
    { refreshable: true },
  )

  return assertAnalyticsData<AnalyticsPatternIssueReportResponse>(result)
}
