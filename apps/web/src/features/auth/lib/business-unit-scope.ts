export type BusinessUnitScopeSelection = {
  scope_type: 'business_unit'
  scope_id: string
}

export type BusinessUnitNode = {
  id: string
  key: string
  label: string
  unit_type: string
  activity_subjects: Array<{
    id: string
    normalized_name: string
    label: string
  }>
}

export type BusinessUnitTree = {
  business_units: BusinessUnitNode[]
}

export function buildBusinessUnitScopeTree(data: BusinessUnitTree) {
  return {
    businessUnits: data.business_units,
    byId: new Map(data.business_units.map((bu) => [bu.id, bu])),
  }
}

export function toggleBusinessUnitScope(
  scopes: BusinessUnitScopeSelection[],
  businessUnitId: string,
): BusinessUnitScopeSelection[] {
  const exists = scopes.some((s) => s.scope_id === businessUnitId)
  if (exists) {
    return scopes.filter((s) => s.scope_id !== businessUnitId)
  }
  return [...scopes, { scope_type: 'business_unit', scope_id: businessUnitId }]
}

export function isBusinessUnitSelected(
  scopes: BusinessUnitScopeSelection[],
  businessUnitId: string,
) {
  return scopes.some((s) => s.scope_id === businessUnitId)
}

export function businessUnitScopesFromApiItems(
  items: Array<{ scope_type: string; scope_id: string }>,
): BusinessUnitScopeSelection[] {
  return items
    .filter(
      (item): item is BusinessUnitScopeSelection => item.scope_type === 'business_unit',
    )
    .map((item) => ({
      scope_type: 'business_unit',
      scope_id: item.scope_id,
    }))
}
