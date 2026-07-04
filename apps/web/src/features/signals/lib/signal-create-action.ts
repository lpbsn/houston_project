/** UI gate for creating an action plan from a signal (CTA + create page). Reads hint `can_create_action`. */
export function shouldShowSignalCreateActionPlan(
  hints: { can_create_action?: boolean } | null | undefined,
): boolean {
  return hints?.can_create_action === true
}
