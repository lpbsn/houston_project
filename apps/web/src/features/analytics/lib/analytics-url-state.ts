import { useMemo } from 'react'

import { useLocationSearch } from '@/lib/location-search'

export const ANALYTICS_PERIOD_START_PARAM = 'period_start'
export const ANALYTICS_PERIOD_END_PARAM = 'period_end'
export const ANALYTICS_ORGANIZATION_ID_PARAM = 'organization_id'
export const ANALYTICS_ESTABLISHMENT_IDS_PARAM = 'establishment_ids'
export const ANALYTICS_SEARCH_PARAM = 'q'
export const ANALYTICS_RECURRENCE_PARAM = 'recurrence'
export const ANALYTICS_RESPONSIBLE_BUSINESS_UNIT_IDS_PARAM = 'responsible_business_unit_ids'
export const ANALYTICS_RESPONSIBLE_BUSINESS_UNIT_UNASSIGNED_PARAM =
  'responsible_business_unit_unassigned'
export const ANALYTICS_SIGNAL_STATUSES_PARAM = 'signal_statuses'
export const ANALYTICS_PATTERN_ID_PARAM = 'analytics_pattern_id'
export const ANALYTICS_DEFAULT_PERIOD_DAYS = 30

export const ANALYTICS_RECURRENCE_VALUES = ['all', 'recurrent', 'non_recurrent'] as const
export type AnalyticsRecurrenceFilter = (typeof ANALYTICS_RECURRENCE_VALUES)[number]

export const ANALYTICS_SIGNAL_STATUS_VALUES = [
  'open',
  'in_progress',
  'interesting',
  'resolved',
  'archived',
] as const
export type AnalyticsSignalStatusFilter = (typeof ANALYTICS_SIGNAL_STATUS_VALUES)[number]

export type AnalyticsUrlState = {
  periodStart: string
  periodEnd: string
  organizationId: string | null
  establishmentIds: string[]
  q: string
  recurrence: AnalyticsRecurrenceFilter
  responsibleBusinessUnitIds: string[]
  responsibleBusinessUnitUnassigned: boolean
  signalStatuses: AnalyticsSignalStatusFilter[]
}

export type AnalyticsSignalReturnContext = {
  patternId: string
  state: AnalyticsUrlState
}

const UUID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i
const ISO_TIMEZONE_SUFFIX_PATTERN = /(Z|[+-]\d{2}:\d{2})$/i
const RECURRENCE_SET = new Set<string>(ANALYTICS_RECURRENCE_VALUES)
const SIGNAL_STATUS_SET = new Set<string>(ANALYTICS_SIGNAL_STATUS_VALUES)

function parseSearchParams(search: string): URLSearchParams {
  return new URLSearchParams(search.startsWith('?') ? search.slice(1) : search)
}

function isValidUuid(value: string | null): value is string {
  return Boolean(value && UUID_PATTERN.test(value.trim()))
}

function parseUuidList(value: string | null): string[] {
  if (!value) {
    return []
  }
  return [...new Set(value.split(',').map((item) => item.trim()).filter(isValidUuid))].sort()
}

function parseStringList<T extends string>(value: string | null, allowed: Set<string>): T[] {
  if (!value) {
    return []
  }
  return [
    ...new Set(
      value
        .split(',')
        .map((item) => item.trim())
        .filter((item) => allowed.has(item)),
    ),
  ].sort() as T[]
}

function parseBoolean(value: string | null): boolean {
  return value === 'true' || value === '1'
}

function parseRecurrence(value: string | null): AnalyticsRecurrenceFilter {
  const normalized = value?.trim()
  return normalized && RECURRENCE_SET.has(normalized)
    ? (normalized as AnalyticsRecurrenceFilter)
    : 'all'
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
  const q = params.get(ANALYTICS_SEARCH_PARAM)?.trim() ?? ''

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
    establishmentIds: parseUuidList(params.get(ANALYTICS_ESTABLISHMENT_IDS_PARAM)),
    q,
    recurrence: parseRecurrence(params.get(ANALYTICS_RECURRENCE_PARAM)),
    responsibleBusinessUnitIds: parseUuidList(
      params.get(ANALYTICS_RESPONSIBLE_BUSINESS_UNIT_IDS_PARAM),
    ),
    responsibleBusinessUnitUnassigned: parseBoolean(
      params.get(ANALYTICS_RESPONSIBLE_BUSINESS_UNIT_UNASSIGNED_PARAM),
    ),
    signalStatuses: parseStringList<AnalyticsSignalStatusFilter>(
      params.get(ANALYTICS_SIGNAL_STATUSES_PARAM),
      SIGNAL_STATUS_SET,
    ),
  }
}

export function buildAnalyticsSearchParams(state: AnalyticsUrlState): URLSearchParams {
  const params = new URLSearchParams()
  params.set(ANALYTICS_PERIOD_START_PARAM, state.periodStart)
  params.set(ANALYTICS_PERIOD_END_PARAM, state.periodEnd)

  if (state.organizationId) {
    params.set(ANALYTICS_ORGANIZATION_ID_PARAM, state.organizationId)
  }
  if (state.establishmentIds.length > 0) {
    params.set(ANALYTICS_ESTABLISHMENT_IDS_PARAM, state.establishmentIds.join(','))
  }
  if (state.q.trim()) {
    params.set(ANALYTICS_SEARCH_PARAM, state.q.trim())
  }
  if (state.recurrence !== 'all') {
    params.set(ANALYTICS_RECURRENCE_PARAM, state.recurrence)
  }
  if (state.responsibleBusinessUnitIds.length > 0) {
    params.set(
      ANALYTICS_RESPONSIBLE_BUSINESS_UNIT_IDS_PARAM,
      state.responsibleBusinessUnitIds.join(','),
    )
  }
  if (state.responsibleBusinessUnitUnassigned) {
    params.set(ANALYTICS_RESPONSIBLE_BUSINESS_UNIT_UNASSIGNED_PARAM, 'true')
  }
  if (state.signalStatuses.length > 0) {
    params.set(ANALYTICS_SIGNAL_STATUSES_PARAM, state.signalStatuses.join(','))
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

export function buildAnalyticsPatternDetailPath(
  patternId: string,
  state: AnalyticsUrlState,
): string {
  const params = buildAnalyticsSearchParams(state)
  const query = params.toString()
  return query
    ? `/analytics/patterns/${encodeURIComponent(patternId)}?${query}`
    : `/analytics/patterns/${encodeURIComponent(patternId)}`
}

export function buildAnalyticsSignalDetailPath(
  signalId: string,
  options: { patternId: string; state: AnalyticsUrlState },
): string {
  const params = buildAnalyticsSearchParams(options.state)
  params.set(ANALYTICS_PATTERN_ID_PARAM, options.patternId)
  const query = params.toString()
  return query
    ? `/signals/${encodeURIComponent(signalId)}?${query}`
    : `/signals/${encodeURIComponent(signalId)}`
}

export function buildAnalyticsSignalActionCreatePath(
  signalId: string,
  options: { patternId: string; state: AnalyticsUrlState },
): string {
  const params = buildAnalyticsSearchParams(options.state)
  params.set(ANALYTICS_PATTERN_ID_PARAM, options.patternId)
  const query = params.toString()
  return query
    ? `/signals/${encodeURIComponent(signalId)}/plan?${query}`
    : `/signals/${encodeURIComponent(signalId)}/plan`
}

export function parseAnalyticsSignalReturnContext(
  search: string,
  options: { now: Date },
): AnalyticsSignalReturnContext | null {
  const params = parseSearchParams(search)
  const patternId = params.get(ANALYTICS_PATTERN_ID_PARAM)?.trim() ?? null
  if (!isValidUuid(patternId)) {
    return null
  }

  return {
    patternId,
    state: parseAnalyticsUrlState(search, options),
  }
}

export function useAnalyticsUrlState(): AnalyticsUrlState {
  const search = useLocationSearch()

  return useMemo(() => parseAnalyticsUrlState(search, { now: new Date() }), [search])
}
