/** UI gate for qualifying signal routing (CTA + sheet). */
export function shouldShowSignalQualifyRouting(
  hints: { can_qualify_routing?: boolean } | null | undefined,
): boolean {
  return hints?.can_qualify_routing === true
}

export function isSignalNeedsQualification(signal: {
  routing_status?: string | null
  status?: string | null
}): boolean {
  return (
    signal.routing_status === 'unassigned' &&
    (signal.status === 'open' || signal.status === 'in_progress')
  )
}

export function canUseNeedsQualificationFeedFilter(role: string | null | undefined): boolean {
  return role === 'owner' || role === 'director' || role === 'manager'
}
