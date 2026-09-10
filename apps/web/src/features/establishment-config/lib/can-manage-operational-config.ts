type MembershipLike = {
  status: string
  role: string
  establishment_id: string
}

export function canManageOperationalConfigForEstablishment({
  memberships,
  establishmentId,
}: {
  memberships: readonly MembershipLike[] | null | undefined
  establishmentId: string
}): boolean {
  return Boolean(
    memberships?.some(
      (membership) =>
        membership.status === 'active' &&
        membership.establishment_id === establishmentId &&
        (membership.role === 'owner' || membership.role === 'director'),
    ),
  )
}
