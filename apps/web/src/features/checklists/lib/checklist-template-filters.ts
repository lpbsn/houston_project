import type { ChecklistTemplateListFilters } from '../types'

export const EMPTY_CHECKLIST_TEMPLATE_FILTERS: ChecklistTemplateListFilters = {}

const UUID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i

export function normalizeChecklistTemplateFilters(
  filters: ChecklistTemplateListFilters,
): ChecklistTemplateListFilters {
  const normalized: ChecklistTemplateListFilters = {}

  const businessUnitId = filters.business_unit_id?.trim()
  if (businessUnitId && UUID_PATTERN.test(businessUnitId)) {
    normalized.business_unit_id = businessUnitId
  }

  if (filters.created_by_me === true) {
    normalized.created_by_me = true
  }

  return normalized
}

export function buildChecklistTemplateListQueryParams(
  filters: ChecklistTemplateListFilters,
): Record<string, string | boolean> {
  const normalized = normalizeChecklistTemplateFilters(filters)

  return {
    ...(normalized.business_unit_id ? { business_unit_id: normalized.business_unit_id } : {}),
    ...(normalized.created_by_me ? { created_by_me: true } : {}),
  }
}
