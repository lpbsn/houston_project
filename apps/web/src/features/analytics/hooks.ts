import { useInfiniteQuery, useMutation, useQuery } from '@tanstack/react-query'

import {
  analyticsQueryKeys,
  fetchAnalyticsDashboard,
  fetchAnalyticsPatternDetail,
  fetchAnalyticsPatternFilterOptions,
  fetchAnalyticsPatternGovernanceTargets,
  fetchAnalyticsPatternSignals,
  fetchAnalyticsPatterns,
  mergeAnalyticsPatterns,
  moveAnalyticsPatternSignals,
  renameAnalyticsPattern,
  reportAnalyticsPatternIssue,
  splitAnalyticsPatternToExisting,
  splitAnalyticsPatternToNew,
} from './api'
import type {
  AnalyticsPatternIssueReportRequest,
  AnalyticsPatternMergeRequest,
  AnalyticsPatternMoveSignalsRequest,
  AnalyticsPatternRenameRequest,
  AnalyticsPatternSplitToExistingRequest,
  AnalyticsPatternSplitToNewRequest,
} from './api'
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

export function useAnalyticsPatternGovernanceTargetsInfiniteQuery(
  patternId: string,
  options?: UseAnalyticsDashboardQueryOptions & { q?: string; pageSize?: number },
) {
  return useInfiniteQuery({
    queryKey: analyticsQueryKeys.governanceTargets(patternId, {
      q: options?.q,
      pageSize: options?.pageSize,
    }),
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam }) =>
      fetchAnalyticsPatternGovernanceTargets(patternId, {
        q: options?.q,
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

export function useRenameAnalyticsPatternMutation() {
  return useMutation({
    mutationFn: ({
      patternId,
      body,
    }: {
      patternId: string
      body: AnalyticsPatternRenameRequest
    }) => renameAnalyticsPattern(patternId, body),
    retry: false,
  })
}

export function useMergeAnalyticsPatternsMutation() {
  return useMutation({
    mutationFn: ({
      patternId,
      body,
    }: {
      patternId: string
      body: AnalyticsPatternMergeRequest
    }) => mergeAnalyticsPatterns(patternId, body),
    retry: false,
  })
}

export function useMoveAnalyticsPatternSignalsMutation() {
  return useMutation({
    mutationFn: ({
      patternId,
      body,
    }: {
      patternId: string
      body: AnalyticsPatternMoveSignalsRequest
    }) => moveAnalyticsPatternSignals(patternId, body),
    retry: false,
  })
}

export function useSplitAnalyticsPatternToExistingMutation() {
  return useMutation({
    mutationFn: ({
      patternId,
      body,
    }: {
      patternId: string
      body: AnalyticsPatternSplitToExistingRequest
    }) => splitAnalyticsPatternToExisting(patternId, body),
    retry: false,
  })
}

export function useSplitAnalyticsPatternToNewMutation() {
  return useMutation({
    mutationFn: ({
      patternId,
      body,
    }: {
      patternId: string
      body: AnalyticsPatternSplitToNewRequest
    }) => splitAnalyticsPatternToNew(patternId, body),
    retry: false,
  })
}
