import { describe, expect, it } from 'vitest'

import {
  buildOperationalConfigPath,
  isValidEstablishmentAdminReturnTo,
  planOpenOperationalConfig,
  resolveOperationalConfigReturnPath,
} from './operational-config-navigation'

const EST_ID = '11111111-1111-4111-8111-111111111111'
const OTHER_ID = '22222222-2222-4222-8222-222222222222'

describe('operational-config-navigation', () => {
  it('validates returnTo allow-list', () => {
    expect(isValidEstablishmentAdminReturnTo(`/organization/establishments/${EST_ID}`)).toBe(
      true,
    )
    expect(isValidEstablishmentAdminReturnTo('/organization')).toBe(false)
    expect(isValidEstablishmentAdminReturnTo('/reporting')).toBe(false)
    expect(isValidEstablishmentAdminReturnTo(`/organization/establishments/${EST_ID}/extra`)).toBe(
      false,
    )
  })

  it('builds ops-config path with returnTo', () => {
    expect(buildOperationalConfigPath(EST_ID)).toBe(
      `/app/operational-config?returnTo=${encodeURIComponent(`/organization/establishments/${EST_ID}`)}`,
    )
  })

  it('resolves return path priority', () => {
    expect(
      resolveOperationalConfigReturnPath({
        returnTo: `/organization/establishments/${EST_ID}`,
        activeEstablishmentId: OTHER_ID,
        canAccessActiveEstablishmentAdmin: true,
      }),
    ).toBe(`/organization/establishments/${EST_ID}`)

    expect(
      resolveOperationalConfigReturnPath({
        returnTo: '/evil',
        activeEstablishmentId: OTHER_ID,
        canAccessActiveEstablishmentAdmin: true,
      }),
    ).toBe(`/organization/establishments/${OTHER_ID}`)

    expect(
      resolveOperationalConfigReturnPath({
        returnTo: null,
        activeEstablishmentId: OTHER_ID,
        canAccessActiveEstablishmentAdmin: false,
      }),
    ).toBe('/reporting')
  })

  it('plans switch only when needed', () => {
    expect(
      planOpenOperationalConfig({
        targetEstablishmentId: EST_ID,
        activeEstablishmentId: EST_ID,
      }).kind,
    ).toBe('already_selected')

    expect(
      planOpenOperationalConfig({
        targetEstablishmentId: EST_ID,
        activeEstablishmentId: OTHER_ID,
      }),
    ).toEqual({
      kind: 'needs_switch',
      establishmentId: EST_ID,
      path: buildOperationalConfigPath(EST_ID),
    })
  })
})
