export function shouldShowSignalCreateActionPlan(
  hints: { can_create_action?: boolean } | null | undefined,
): boolean {
  return hints?.can_create_action === true
}
