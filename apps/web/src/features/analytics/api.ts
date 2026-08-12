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

export type AnalyticsPatternFilterOptionsResponse = {
  establishments: Array<{
    establishment_id: string
    name: string
  }>
  responsible_business_units: Array<{
    business_unit_id: string | null
    name: string
    establishment_id: string | null
    is_unassigned: boolean
  }>
  includes_unassigned: boolean
}

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
          query: buildPatternListQuery(state, options) as never,
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
      // The path is generated after the Ticket 27 schema regeneration.
      apiClient.GET('/api/v1/analytics/pattern-filter-options/' as never, {
        params: {
          query: buildPatternFilterOptionsQuery(state),
        },
        headers: getAuthHeaders(accessToken),
      } as never),
    { refreshable: true },
  )

  return assertAnalyticsData<AnalyticsPatternFilterOptionsResponse>(result)
}
