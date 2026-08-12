import { useQuery } from '@tanstack/react-query'

import { analyticsQueryKeys, fetchAnalyticsDashboard } from './api'
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
