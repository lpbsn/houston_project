import { apiClient, withAuthRetry } from '@/api/client'
import type { components } from '@/api/generated/types'
import { parseStandardApiError } from '@/lib/api-errors'

import type { AnalyticsUrlState } from './lib/analytics-url-state'

export type AnalyticsDashboardResponse =
  components['schemas']['AnalyticsDashboardResponse']
export type AnalyticsKPIResult = components['schemas']['AnalyticsKPIResult']
export type AnalyticsMetricComparison =
  components['schemas']['AnalyticsMetricComparison']

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

export async function fetchAnalyticsDashboard(
  state: AnalyticsUrlState,
): Promise<AnalyticsDashboardResponse> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.GET('/api/v1/analytics/dashboard/', {
        params: {
          query: {
            period_start: state.periodStart,
            period_end: state.periodEnd,
            ...(state.organizationId ? { organization_id: state.organizationId } : {}),
          },
        },
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )

  return assertAnalyticsData<AnalyticsDashboardResponse>(result)
}
