type BusinessUnitOption = {
  id: string
  label: string
  key?: string
}

type MembershipScope = {
  scope_type: string
  scope_id: string
}

export function shouldFilterBusinessUnitsByMembershipScope(
  role: string | null | undefined,
): boolean {
  return role === 'manager' || role === 'staff'
}

export function resolveVisibleBusinessUnits(options: {
  role: string | null | undefined
  scopes: MembershipScope[] | undefined
  businessUnits: BusinessUnitOption[]
  filterByScope?: boolean
}): BusinessUnitOption[] {
  const { role, scopes, businessUnits } = options
  const filterByScope =
    options.filterByScope ?? shouldFilterBusinessUnitsByMembershipScope(role)

  if (!filterByScope) {
    return businessUnits
  }

  const membershipScopes = scopes ?? []
  if (membershipScopes.length === 0) {
    return businessUnits
  }

  return businessUnits.filter((unit) =>
    membershipScopes.some(
      (scope) => scope.scope_type === 'business_unit' && scope.scope_id === unit.id,
    ),
  )
}
