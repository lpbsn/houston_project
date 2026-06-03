export type SignalFeedStatusFilter = 'open' | 'in_progress' | 'resolved'

export type SignalFeedFilters = {
  statuses: SignalFeedStatusFilter[]
  moduleKeys: string[]
  domainKeys: string[]
  subjectKeys: string[]
}

export const EMPTY_SIGNAL_FEED_FILTERS: SignalFeedFilters = {
  statuses: [],
  moduleKeys: [],
  domainKeys: [],
  subjectKeys: [],
}

export const SIGNAL_FEED_STATUS_OPTIONS: ReadonlyArray<{
  value: SignalFeedStatusFilter
  label: string
}> = [
  { value: 'open', label: 'En attente' },
  { value: 'in_progress', label: 'En cours' },
  { value: 'resolved', label: 'Résolu' },
]

const FEED_STATUS_SET = new Set<string>(SIGNAL_FEED_STATUS_OPTIONS.map((option) => option.value))

function dedupeSorted(values: string[]): string[] {
  return [...new Set(values.map((value) => value.trim()).filter(Boolean))].sort()
}

export function normalizeSignalFeedFilters(filters: SignalFeedFilters): SignalFeedFilters {
  return {
    statuses: dedupeSorted(filters.statuses).filter((value): value is SignalFeedStatusFilter =>
      FEED_STATUS_SET.has(value),
    ),
    moduleKeys: dedupeSorted(filters.moduleKeys),
    domainKeys: dedupeSorted(filters.domainKeys),
    subjectKeys: dedupeSorted(filters.subjectKeys),
  }
}

export function hasActiveSignalFeedFilters(filters: SignalFeedFilters): boolean {
  const normalized = normalizeSignalFeedFilters(filters)
  return (
    normalized.statuses.length > 0 ||
    normalized.moduleKeys.length > 0 ||
    normalized.domainKeys.length > 0 ||
    normalized.subjectKeys.length > 0
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
  if (normalized.moduleKeys.length > 0) {
    params.set('module_keys', normalized.moduleKeys.join(','))
  }
  if (normalized.domainKeys.length > 0) {
    params.set('domain_keys', normalized.domainKeys.join(','))
  }
  if (normalized.subjectKeys.length > 0) {
    params.set('subject_keys', normalized.subjectKeys.join(','))
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

export function countCategoryFilterSelections(filters: SignalFeedFilters): number {
  const normalized = normalizeSignalFeedFilters(filters)
  return (
    normalized.moduleKeys.length + normalized.domainKeys.length + normalized.subjectKeys.length
  )
}

export function formatCategoryFilterSummary(
  filters: SignalFeedFilters,
  labelByKey: Map<string, string>,
): string {
  const normalized = normalizeSignalFeedFilters(filters)
  const count = countCategoryFilterSelections(normalized)
  if (count === 0) {
    return 'Toutes ▾'
  }

  const orderedKeys = [
    ...normalized.moduleKeys,
    ...normalized.domainKeys,
    ...normalized.subjectKeys,
  ]
  const firstLabel = labelByKey.get(orderedKeys[0] ?? '') ?? orderedKeys[0]

  if (count === 1) {
    return firstLabel ? `${firstLabel} ▾` : '1 catégorie ▾'
  }
  if (count <= 3) {
    return `${count} catégories ▾`
  }
  return firstLabel ? `${firstLabel} +${count - 1} ▾` : `${count} catégories ▾`
}
