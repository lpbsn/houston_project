import { describe, expect, it } from 'vitest'

import {
  ESTABLISHMENT_APP_HOME_PATH,
  planOpenEstablishmentApp,
} from './open-establishment-app-navigation'

const EST_ID = '11111111-1111-4111-8111-111111111111'
const OTHER_ID = '22222222-2222-4222-8222-222222222222'

describe('planOpenEstablishmentApp', () => {
  it('returns already_selected when target is active', () => {
    expect(
      planOpenEstablishmentApp({
        targetEstablishmentId: EST_ID,
        activeEstablishmentId: EST_ID,
      }),
    ).toEqual({
      kind: 'already_selected',
      path: ESTABLISHMENT_APP_HOME_PATH,
    })
  })

  it('returns needs_switch when target differs from active', () => {
    expect(
      planOpenEstablishmentApp({
        targetEstablishmentId: EST_ID,
        activeEstablishmentId: OTHER_ID,
      }),
    ).toEqual({
      kind: 'needs_switch',
      establishmentId: EST_ID,
      path: ESTABLISHMENT_APP_HOME_PATH,
    })
  })

  it('returns needs_switch when no active establishment', () => {
    expect(
      planOpenEstablishmentApp({
        targetEstablishmentId: EST_ID,
        activeEstablishmentId: null,
      }),
    ).toEqual({
      kind: 'needs_switch',
      establishmentId: EST_ID,
      path: '/reporting',
    })
  })
})
