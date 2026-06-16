export function canAccessChecklistLibrary(options: {
  establishmentId: string | null | undefined
  activeMembershipId: string | null | undefined
}): boolean {
  return Boolean(options.establishmentId && options.activeMembershipId)
}
