export type SignalFeedStatusFilter = 'open' | 'in_progress' | 'resolved' | 'canceled'

export type SignalFeedFilters = {
  statuses: SignalFeedStatusFilter[]
  businessUnitIds: string[]
  activitySubjectIds: string[]
}

export const EMPTY_SIGNAL_FEED_FILTERS: SignalFeedFilters = {
  statuses: [],
  businessUnitIds: [],
  activitySubjectIds: [],
}

export const SIGNAL_FEED_STATUS_OPTIONS: ReadonlyArray<{
  value: SignalFeedStatusFilter
  label: string
}> = [
  { value: 'open', label: 'En attente' },
  { value: 'in_progress', label: 'En cours' },
  { value: 'resolved', label: 'Résolue' },
  { value: 'canceled', label: 'Annulée' },
]

const FEED_STATUS_SET = new Set<string>(SIGNAL_FEED_STATUS_OPTIONS.map((option) => option.value))
const UUID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i

function dedupeSorted(values: string[]): string[] {
  return [...new Set(values.map((value) => value.trim()).filter(Boolean))].sort()
}

export function normalizeSignalFeedFilters(filters: SignalFeedFilters): SignalFeedFilters {
  return {
    statuses: dedupeSorted(filters.statuses).filter((value): value is SignalFeedStatusFilter =>
      FEED_STATUS_SET.has(value),
    ),
    businessUnitIds: dedupeSorted(filters.businessUnitIds).filter((value) =>
      UUID_PATTERN.test(value),
    ),
    activitySubjectIds: dedupeSorted(filters.activitySubjectIds).filter((value) =>
      UUID_PATTERN.test(value),
    ),
  }
}

export function hasActiveSignalFeedFilters(filters: SignalFeedFilters): boolean {
  const normalized = normalizeSignalFeedFilters(filters)
  return (
    normalized.statuses.length > 0 ||
    normalized.businessUnitIds.length > 0 ||
    normalized.activitySubjectIds.length > 0
  )
}

export function appendSignalFeedFiltersToSearchParams(
  params: URLSearchParams,
  filters: SignalFeedFilters,
): void {
  const normalized = normalizeSignalFeedFilters(filters)
  if (normalized.statuses.length > 0) {
    params.set('statuses', normalized.statuses.join(','))
  }
  if (normalized.businessUnitIds.length > 0) {
    params.set('business_unit_ids', normalized.businessUnitIds.join(','))
  }
  if (normalized.activitySubjectIds.length > 0) {
    params.set('activity_subject_ids', normalized.activitySubjectIds.join(','))
  }
}

export function formatStatusFilterSummary(filters: SignalFeedFilters): string {
  const { statuses } = normalizeSignalFeedFilters(filters)
  if (statuses.length === 0) {
    return 'Tous ▾'
  }
  if (statuses.length === 1) {
    const label = SIGNAL_FEED_STATUS_OPTIONS.find((option) => option.value === statuses[0])?.label
    return `${label ?? statuses[0]} ▾`
  }
  return `${statuses.length} sélectionnés ▾`
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
