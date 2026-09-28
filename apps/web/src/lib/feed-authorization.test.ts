import { describe, expect, it } from 'vitest'

import { feedAuthorizationFingerprint } from './feed-authorization'

describe('feedAuthorizationFingerprint', () => {
  it('changes when role or scopes change and stays stable for the same membership', () => {
    const base = feedAuthorizationFingerprint({
      id: 'm-1',
      establishment_id: 'est-1',
      role: 'staff',
      status: 'active',
      scopes: [
        { scope_type: 'business_unit', scope_id: 'bu-2' },
        { scope_type: 'business_unit', scope_id: 'bu-1' },
      ],
    })
    const reordered = feedAuthorizationFingerprint({
      id: 'm-1',
      establishment_id: 'est-1',
      role: 'staff',
      status: 'active',
      scopes: [
        { scope_type: 'business_unit', scope_id: 'bu-1' },
        { scope_type: 'business_unit', scope_id: 'bu-2' },
      ],
    })
    const roleChanged = feedAuthorizationFingerprint({
      id: 'm-1',
      establishment_id: 'est-1',
      role: 'manager',
      status: 'active',
      scopes: [{ scope_type: 'business_unit', scope_id: 'bu-1' }],
    })

    expect(reordered).toBe(base)
    expect(roleChanged).not.toBe(base)
    expect(feedAuthorizationFingerprint(null)).toBe('none')
  })

  it('changes when another membership in the bootstrap list changes', () => {
    const memberships = [
      { id: 'm-1', establishment_id: 'est-1', role: 'staff', status: 'active', scopes: [] },
      { id: 'm-2', establishment_id: 'est-2', role: 'manager', status: 'active', scopes: [] },
    ]
    const changed = [
      memberships[0]!,
      { ...memberships[1]!, role: 'director' },
    ]
    expect(feedAuthorizationFingerprint(changed)).not.toBe(
      feedAuthorizationFingerprint(memberships),
    )
    expect(feedAuthorizationFingerprint([...memberships].reverse())).toBe(
      feedAuthorizationFingerprint(memberships),
    )
  })
})
