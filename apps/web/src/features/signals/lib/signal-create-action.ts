/** UI gate for creating an action plan from a signal (CTA + create page). */
export function shouldShowSignalCreateActionPlan(
  hints: { can_create_linked_action_plan?: boolean } | null | undefined,
): boolean {
  return hints?.can_create_linked_action_plan === true
}
