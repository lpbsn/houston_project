export type SignalFeedStatusFilter =
  | 'open'
  | 'in_progress'
  | 'interesting'
  | 'resolved'
  | 'canceled'

export type SignalFeedStatusSelection = 'all' | SignalFeedStatusFilter

export type SignalFeedFilters = {
  statuses: SignalFeedStatusFilter[]
  businessUnitIds: string[]
  activitySubjectIds: string[]
  needsQualification: boolean
}

export const EMPTY_SIGNAL_FEED_FILTERS: SignalFeedFilters = {
  statuses: [],
  businessUnitIds: [],
  activitySubjectIds: [],
  needsQualification: false,
}

export const SIGNAL_FEED_STATUS_OPTIONS: ReadonlyArray<{
  value: SignalFeedStatusFilter
  label: string
}> = [
  { value: 'open', label: 'Ouverts' },
  { value: 'in_progress', label: 'En cours' },
  { value: 'interesting', label: 'Intéressants' },
]

const FILTERABLE_STATUS_ORDER: SignalFeedStatusFilter[] = [
  'open',
  'in_progress',
  'interesting',
  'resolved',
  'canceled',
]

const UUID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i

function dedupeSorted(values: string[]): string[] {
  return [...new Set(values.map((value) => value.trim()).filter(Boolean))].sort()
}

export function normalizeSignalFeedFilters(filters: SignalFeedFilters): SignalFeedFilters {
  const allowed = FILTERABLE_STATUS_ORDER.filter((status) => filters.statuses.includes(status))
  return {
    statuses: allowed.slice(0, 1),
    businessUnitIds: dedupeSorted(filters.businessUnitIds).filter((value) =>
      UUID_PATTERN.test(value),
    ),
    activitySubjectIds: dedupeSorted(filters.activitySubjectIds).filter((value) =>
      UUID_PATTERN.test(value),
    ),
    needsQualification: filters.needsQualification === true,
  }
}

export function hasActiveSignalFeedFilters(filters: SignalFeedFilters): boolean {
  const normalized = normalizeSignalFeedFilters(filters)
  return (
    normalized.statuses.length > 0 ||
    normalized.businessUnitIds.length > 0 ||
    normalized.activitySubjectIds.length > 0 ||
    normalized.needsQualification
  )
}

export function selectedSignalFeedStatus(
  filters: SignalFeedFilters,
): SignalFeedStatusSelection {
  return normalizeSignalFeedFilters(filters).statuses[0] ?? 'all'
}

export function signalFeedFiltersForStatus(
  filters: SignalFeedFilters,
  status: SignalFeedStatusSelection,
): SignalFeedFilters {
  return normalizeSignalFeedFilters({
    ...filters,
    statuses: status === 'all' ? [] : [status],
  })
}

export function countClassificationFilterSelections(filters: SignalFeedFilters): number {
  const normalized = normalizeSignalFeedFilters(filters)
  return normalized.businessUnitIds.length + normalized.activitySubjectIds.length
}

export function formatClassificationFilterSummary(
  filters: SignalFeedFilters,
  labelByBusinessUnitId: Map<string, string>,
  labelByActivitySubjectId: Map<string, string>,
): string {
  const normalized = normalizeSignalFeedFilters(filters)
  const count = countClassificationFilterSelections(normalized)
  if (count === 0) {
    return 'Tous ▾'
  }

  const orderedLabels = [
    ...normalized.businessUnitIds.map((id) => labelByBusinessUnitId.get(id) ?? id),
    ...normalized.activitySubjectIds.map((id) => labelByActivitySubjectId.get(id) ?? id),
  ]
  const firstLabel = orderedLabels[0]

  if (count === 1) {
    return firstLabel ? `${firstLabel} ▾` : '1 sélection ▾'
  }
  if (count <= 3) {
    return `${count} sélections ▾`
  }
  return firstLabel ? `${firstLabel} +${count - 1} ▾` : `${count} sélections ▾`
}

/** Compact chip label without dropdown chevron (mobile filter chips). */
export function formatClassificationFilterChipLabel(
  filters: SignalFeedFilters,
  labelByBusinessUnitId: Map<string, string>,
  labelByActivitySubjectId: Map<string, string>,
): string {
  const normalized = normalizeSignalFeedFilters(filters)
  const count = countClassificationFilterSelections(normalized)
  if (count === 0) {
    return 'Pôle / Sujet'
  }

  const orderedLabels = [
    ...normalized.businessUnitIds.map((id) => labelByBusinessUnitId.get(id) ?? id),
    ...normalized.activitySubjectIds.map((id) => labelByActivitySubjectId.get(id) ?? id),
  ]
  const firstLabel = orderedLabels[0]

  if (count === 1) {
    return firstLabel ?? '1 sélection'
  }
  if (count <= 3) {
    return `Pôle / Sujet · ${count}`
  }
  return firstLabel ? `${firstLabel} +${count - 1}` : `Pôle / Sujet · ${count}`
}
