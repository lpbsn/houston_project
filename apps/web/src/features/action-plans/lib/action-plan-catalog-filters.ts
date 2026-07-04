import type { ActionPlanCatalogListFilters } from '../types'

export function normalizeActionPlanCatalogFilters(
  filters: ActionPlanCatalogListFilters = {},
): ActionPlanCatalogListFilters {
  const normalized: ActionPlanCatalogListFilters = {}
  if (filters.business_unit_id) {
    normalized.business_unit_id = filters.business_unit_id
  }
  if (filters.created_by_me) {
    normalized.created_by_me = true
  }
  return normalized
}

export function buildActionPlanCatalogListQueryParams(
  filters: ActionPlanCatalogListFilters = {},
): Record<string, string | boolean> {
  const normalized = normalizeActionPlanCatalogFilters(filters)
  const query: Record<string, string | boolean> = {}
  if (normalized.business_unit_id) {
    query.business_unit_id = normalized.business_unit_id
  }
  if (normalized.created_by_me) {
    query.created_by_me = true
  }
  return query
}

export function filterActionPlansByTitle<T extends { title: string }>(
  items: T[],
  searchQuery: string,
): T[] {
  const normalized = searchQuery.trim().toLowerCase()
  if (!normalized) {
    return items
  }
  return items.filter((item) => item.title.toLowerCase().includes(normalized))
}
