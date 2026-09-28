export type FeedAuthorizationMembership = {
  id?: string | null
  establishment_id?: string | null
  role?: string | null
  status?: string | null
  scopes?: readonly { scope_type?: string | null; scope_id?: string | null }[] | null
}

function membershipFingerprint(membership: FeedAuthorizationMembership): string | null {
  if (!membership.id) {
    return null
  }
  const scopes = [...(membership.scopes ?? [])]
    .map((scope) => `${scope.scope_type ?? ''}:${scope.scope_id ?? ''}`)
    .sort()
    .join(',')
  return [
    membership.id,
    membership.establishment_id ?? '',
    membership.role ?? '',
    membership.status ?? '',
    scopes,
  ].join('|')
}

/**
 * Local stand-in for the server authorization fingerprint.
 * A change drops feed cursors. Cross depends on every contributing membership,
 * so the client hashes the whole bootstrap membership list.
 */
export function feedAuthorizationFingerprint(
  memberships:
    | FeedAuthorizationMembership
    | readonly FeedAuthorizationMembership[]
    | null
    | undefined,
): string {
  const list = memberships == null ? [] : Array.isArray(memberships) ? memberships : [memberships]
  const rows = list
    .map((membership) => membershipFingerprint(membership))
    .filter((row): row is string => row != null)
    .sort()
  return rows.length > 0 ? rows.join('\n') : 'none'
}
