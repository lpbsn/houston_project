import { useMemo } from 'react'

import { useLocationSearch } from '@/lib/location-search'

export const DASHBOARD_PERIOD_DAYS = [3, 7, 15, 30, 90] as const
export type DashboardPeriodDays = (typeof DASHBOARD_PERIOD_DAYS)[number]
export const DEFAULT_DASHBOARD_PERIOD_DAYS: DashboardPeriodDays = 7
export const DASHBOARD_PERIOD_PARAM = 'period'

const PERIOD_SET = new Set<number>(DASHBOARD_PERIOD_DAYS)

function parseSearchParams(search: string): URLSearchParams {
  return new URLSearchParams(search.startsWith('?') ? search.slice(1) : search)
}

export function parseDashboardPeriodDays(search: string): DashboardPeriodDays {
  const raw = parseSearchParams(search).get(DASHBOARD_PERIOD_PARAM)
  if (!raw) {
    return DEFAULT_DASHBOARD_PERIOD_DAYS
  }
  const match = raw.trim().match(/^(\d+)d$/i)
  if (!match?.[1]) {
    return DEFAULT_DASHBOARD_PERIOD_DAYS
  }
  const days = Number(match[1])
  if (!PERIOD_SET.has(days)) {
    return DEFAULT_DASHBOARD_PERIOD_DAYS
  }
  return days as DashboardPeriodDays
}

export function buildDashboardSearch(periodDays: DashboardPeriodDays): string {
  if (periodDays === DEFAULT_DASHBOARD_PERIOD_DAYS) {
    return `?${DASHBOARD_PERIOD_PARAM}=${periodDays}d`
  }
  return `?${DASHBOARD_PERIOD_PARAM}=${periodDays}d`
}

export function buildDashboardHref(pathname: string, periodDays: DashboardPeriodDays): string {
  return `${pathname}${buildDashboardSearch(periodDays)}`
}

export function useDashboardPeriodDays(): DashboardPeriodDays {
  const search = useLocationSearch()
  return useMemo(() => parseDashboardPeriodDays(search), [search])
}
