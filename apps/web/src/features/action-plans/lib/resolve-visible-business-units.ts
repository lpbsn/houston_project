type BusinessUnitOption = {
  id: string
  label: string
  key?: string
}

type MembershipScope = {
  scope_type: string
  scope_id: string
}

type BusinessUnitWithSubjects = {
  id: string
  activity_subjects?: Array<{ id: string }>
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

  const membershipScopes = (scopes ?? []).filter(
    (scope) => scope.scope_type === 'business_unit',
  )
  if (membershipScopes.length === 0) {
    // Manager/Staff without an active business-unit scope see no poles.
    return []
  }

  return businessUnits.filter((unit) =>
    membershipScopes.some((scope) => scope.scope_id === unit.id),
  )
}

/** Resolve owning business unit id for an activity subject from the BU tree. */
export function findBusinessUnitIdForActivitySubject(
  businessUnits: BusinessUnitWithSubjects[],
  activitySubjectId: string | null | undefined,
): string | null {
  if (!activitySubjectId) {
    return null
  }
  for (const unit of businessUnits) {
    if (unit.activity_subjects?.some((subject) => subject.id === activitySubjectId)) {
      return unit.id
    }
  }
  return null
}

/**
 * When linked create has an activity subject and no responsible, constrain pilot
 * options to that subject's business unit (intersected with visible units).
 */
export function resolveLinkedCreatePilotBusinessUnits(options: {
  visibleBusinessUnits: BusinessUnitOption[]
  activitySubjectBusinessUnitId?: string | null
}): BusinessUnitOption[] {
  const subjectBuId = options.activitySubjectBusinessUnitId
  if (!subjectBuId) {
    return options.visibleBusinessUnits
  }
  return options.visibleBusinessUnits.filter((unit) => unit.id === subjectBuId)
}
