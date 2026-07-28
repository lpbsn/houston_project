import { describe, expect, it } from 'vitest'

import {
  displayEstablishmentName,
  isTechnicalEstablishmentName,
} from './display-establishment-name'

describe('display-establishment-name', () => {
  it('detects draft-* technical names', () => {
    expect(isTechnicalEstablishmentName('draft-11111111-2222-3333-4444-555555555555')).toBe(
      true,
    )
    expect(isTechnicalEstablishmentName('Hotel Nord')).toBe(false)
  })

  it('never returns draft-* labels', () => {
    expect(
      displayEstablishmentName({
        establishmentName: 'draft-aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
        organizationName: 'Northwind Group',
      }),
    ).toBe('Northwind Group')

    expect(
      displayEstablishmentName({
        establishmentName: 'draft-aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
      }),
    ).toBe('Votre établissement')
  })

  it('keeps real establishment names', () => {
    expect(
      displayEstablishmentName({
        establishmentName: 'Hôtel Nord',
        organizationName: 'Northwind Group',
      }),
    ).toBe('Hôtel Nord')
  })
})
