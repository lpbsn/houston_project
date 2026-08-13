import { useInfiniteQuery, useMutation, useQuery } from '@tanstack/react-query'

import {
  analyticsQueryKeys,
  fetchAnalyticsDashboard,
  fetchAnalyticsPatternDetail,
  fetchAnalyticsPatternFilterOptions,
  fetchAnalyticsPatternSignals,
  fetchAnalyticsPatterns,
  reportAnalyticsPatternIssue,
} from './api'
import type { AnalyticsPatternIssueReportRequest } from './api'
import type { AnalyticsUrlState } from './lib/analytics-url-state'

type UseAnalyticsDashboardQueryOptions = {
  enabled?: boolean
}

export function useAnalyticsDashboardQuery(
  state: AnalyticsUrlState,
  options?: UseAnalyticsDashboardQueryOptions,
) {
  return useQuery({
    queryKey: analyticsQueryKeys.dashboard(state),
    queryFn: () => fetchAnalyticsDashboard(state),
    enabled: options?.enabled ?? true,
  })
}

export function useAnalyticsPatternsInfiniteQuery(
  state: AnalyticsUrlState,
  options?: UseAnalyticsDashboardQueryOptions & { pageSize?: number },
) {
  return useInfiniteQuery({
    queryKey: analyticsQueryKeys.patterns(state, options?.pageSize),
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam }) =>
      fetchAnalyticsPatterns(state, {
        cursor: pageParam,
        pageSize: options?.pageSize,
      }),
    getNextPageParam: (lastPage) => {
      if (!lastPage.has_more || !lastPage.next_cursor) {
        return undefined
      }
      return lastPage.next_cursor
    },
    enabled: options?.enabled ?? true,
  })
}

export function useAnalyticsPatternFilterOptionsQuery(
  state: AnalyticsUrlState,
  options?: UseAnalyticsDashboardQueryOptions,
) {
  return useQuery({
    queryKey: analyticsQueryKeys.patternFilterOptions(state),
    queryFn: () => fetchAnalyticsPatternFilterOptions(state),
    enabled: options?.enabled ?? true,
  })
}

export function useAnalyticsPatternDetailQuery(
  patternId: string,
  state: AnalyticsUrlState,
  options?: UseAnalyticsDashboardQueryOptions,
) {
  return useQuery({
    queryKey: analyticsQueryKeys.patternDetail(patternId, state),
    queryFn: () => fetchAnalyticsPatternDetail(patternId, state),
    enabled: options?.enabled ?? true,
  })
}

export function useAnalyticsPatternSignalsInfiniteQuery(
  patternId: string,
  state: AnalyticsUrlState,
  options?: UseAnalyticsDashboardQueryOptions & { pageSize?: number },
) {
  return useInfiniteQuery({
    queryKey: analyticsQueryKeys.patternSignals(patternId, state, options?.pageSize),
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam }) =>
      fetchAnalyticsPatternSignals(patternId, state, {
        cursor: pageParam,
        pageSize: options?.pageSize,
      }),
    getNextPageParam: (lastPage) => {
      if (!lastPage.has_more || !lastPage.next_cursor) {
        return undefined
      }
      return lastPage.next_cursor
    },
    enabled: options?.enabled ?? true,
  })
}

export function useReportAnalyticsPatternIssueMutation() {
  return useMutation({
    mutationFn: ({
      patternId,
      signalId,
      body,
    }: {
      patternId: string
      signalId: string
      body: AnalyticsPatternIssueReportRequest
    }) => reportAnalyticsPatternIssue(patternId, signalId, body),
    retry: false,
  })
}
