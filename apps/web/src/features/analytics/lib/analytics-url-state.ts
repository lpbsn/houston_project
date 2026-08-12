import { useMemo } from 'react'

import { useLocationSearch } from '@/lib/location-search'

export const ANALYTICS_PERIOD_START_PARAM = 'period_start'
export const ANALYTICS_PERIOD_END_PARAM = 'period_end'
export const ANALYTICS_ORGANIZATION_ID_PARAM = 'organization_id'
export const ANALYTICS_DEFAULT_PERIOD_DAYS = 30

export type AnalyticsUrlState = {
  periodStart: string
  periodEnd: string
  organizationId: string | null
}

const UUID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i
const ISO_TIMEZONE_SUFFIX_PATTERN = /(Z|[+-]\d{2}:\d{2})$/i

function parseSearchParams(search: string): URLSearchParams {
  return new URLSearchParams(search.startsWith('?') ? search.slice(1) : search)
}

function isValidUuid(value: string | null): value is string {
  return Boolean(value && UUID_PATTERN.test(value.trim()))
}

function parseAwareDateTime(value: string | null): Date | null {
  const trimmed = value?.trim()
  if (!trimmed || !ISO_TIMEZONE_SUFFIX_PATTERN.test(trimmed)) {
    return null
  }

  const parsed = new Date(trimmed)
  if (Number.isNaN(parsed.getTime())) {
    return null
  }

  return parsed
}

function buildDefaultPeriod(now: Date): Pick<AnalyticsUrlState, 'periodStart' | 'periodEnd'> {
  const periodEnd = new Date(now)
  const periodStart = new Date(periodEnd)
  periodStart.setUTCDate(periodStart.getUTCDate() - ANALYTICS_DEFAULT_PERIOD_DAYS)

  return {
    periodStart: periodStart.toISOString(),
    periodEnd: periodEnd.toISOString(),
  }
}

export function parseAnalyticsUrlState(
  search: string,
  options: { now: Date },
): AnalyticsUrlState {
  const params = parseSearchParams(search)
  const defaultPeriod = buildDefaultPeriod(options.now)
  const parsedStart = parseAwareDateTime(params.get(ANALYTICS_PERIOD_START_PARAM))
  const parsedEnd = parseAwareDateTime(params.get(ANALYTICS_PERIOD_END_PARAM))
  const organizationId = params.get(ANALYTICS_ORGANIZATION_ID_PARAM)?.trim() ?? null

  const hasValidPeriod = parsedStart && parsedEnd && parsedStart.getTime() < parsedEnd.getTime()
  const period = hasValidPeriod
    ? {
        periodStart: parsedStart.toISOString(),
        periodEnd: parsedEnd.toISOString(),
      }
    : defaultPeriod

  return {
    ...period,
    organizationId: isValidUuid(organizationId) ? organizationId : null,
  }
}

export function buildAnalyticsSearchParams(state: AnalyticsUrlState): URLSearchParams {
  const params = new URLSearchParams()
  params.set(ANALYTICS_PERIOD_START_PARAM, state.periodStart)
  params.set(ANALYTICS_PERIOD_END_PARAM, state.periodEnd)

  if (state.organizationId) {
    params.set(ANALYTICS_ORGANIZATION_ID_PARAM, state.organizationId)
  }

  return params
}

export function buildAnalyticsPath(state: AnalyticsUrlState): string {
  const params = buildAnalyticsSearchParams(state)
  const query = params.toString()
  return query ? `/analytics?${query}` : '/analytics'
}

export function buildAnalyticsReturnPath(state: AnalyticsUrlState): string {
  return buildAnalyticsPath(state)
}

export function useAnalyticsUrlState(): AnalyticsUrlState {
  const search = useLocationSearch()

  return useMemo(() => parseAnalyticsUrlState(search, { now: new Date() }), [search])
}
