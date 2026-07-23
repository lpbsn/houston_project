import { describe, expect, it } from 'vitest'

import {
  canAccessEstablishmentAdminPage,
  resolveEstablishmentAdminActorRole,
} from './can-access-establishment-admin'

const membership = (
  establishmentId: string,
  role: string,
  status = 'active',
) => ({
  id: `${establishmentId}-${role}`,
  establishment_id: establishmentId,
  establishment_name: 'Hotel',
  organization_id: 'org-1',
  organization_name: 'Org',
  role,
  status,
  scopes: [],
  scope_summary: { business_unit_count: 0 },
})

describe('canAccessEstablishmentAdminPage', () => {
  it('allows organization owners', () => {
    expect(
      canAccessEstablishmentAdminPage({
        canManageOrganization: true,
        memberships: [],
        establishmentId: 'est-1',
      }),
    ).toBe(true)
  })

  it('allows director with active membership on path establishment', () => {
    expect(
      canAccessEstablishmentAdminPage({
        canManageOrganization: false,
        memberships: [membership('est-1', 'director')],
        establishmentId: 'est-1',
      }),
    ).toBe(true)
  })

  it('rejects director of another establishment', () => {
    expect(
      canAccessEstablishmentAdminPage({
        canManageOrganization: false,
        memberships: [membership('est-2', 'director')],
        establishmentId: 'est-1',
      }),
    ).toBe(false)
  })
})

describe('resolveEstablishmentAdminActorRole', () => {
  it('returns owner for organization managers', () => {
    expect(
      resolveEstablishmentAdminActorRole({
        canManageOrganization: true,
        memberships: [membership('est-1', 'director')],
        establishmentId: 'est-1',
      }),
    ).toBe('owner')
  })

  it('returns director for path director membership', () => {
    expect(
      resolveEstablishmentAdminActorRole({
        canManageOrganization: false,
        memberships: [membership('est-1', 'director')],
        establishmentId: 'est-1',
      }),
    ).toBe('director')
  })
})
