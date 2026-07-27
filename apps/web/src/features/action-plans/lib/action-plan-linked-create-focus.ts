/**
 * Mirrors backend routing_status_for_classification for linked create:
 * resolved iff affected + responsible(pilot) + activity_subject are all set,
 * and pilot matches the subject's business unit when that BU is known.
 */
export function isLinkedCreateEffectiveRoutingResolved(input: {
  affectedBusinessUnitId?: string | null
  activitySubjectId?: string | null
  pilotBusinessUnitId?: string | null
  activitySubjectBusinessUnitId?: string | null
}): boolean {
  if (
    !input.affectedBusinessUnitId ||
    !input.activitySubjectId ||
    !input.pilotBusinessUnitId
  ) {
    return false
  }
  if (
    input.activitySubjectBusinessUnitId &&
    input.pilotBusinessUnitId !== input.activitySubjectBusinessUnitId
  ) {
    return false
  }
  return true
}

export function normalizeLinkedCreateIssueFocus(value: string | null | undefined): string {
  return (value ?? '').trim().toLowerCase().split(/\s+/).filter(Boolean).join(' ')
}

/** Focus field is required in the form only when routing becomes resolved and signal has none. */
export function isLinkedCreateIssueFocusRequired(input: {
  affectedBusinessUnitId?: string | null
  activitySubjectId?: string | null
  pilotBusinessUnitId?: string | null
  activitySubjectBusinessUnitId?: string | null
  signalIssueFocus?: string | null
}): boolean {
  if (
    !isLinkedCreateEffectiveRoutingResolved({
      affectedBusinessUnitId: input.affectedBusinessUnitId,
      activitySubjectId: input.activitySubjectId,
      pilotBusinessUnitId: input.pilotBusinessUnitId,
      activitySubjectBusinessUnitId: input.activitySubjectBusinessUnitId,
    })
  ) {
    return false
  }
  return normalizeLinkedCreateIssueFocus(input.signalIssueFocus).length === 0
}
