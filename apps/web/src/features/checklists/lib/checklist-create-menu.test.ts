import { describe, expect, it } from 'vitest'

import { getChecklistCreateMenuOptions } from './checklist-create-menu'

describe('checklist-create-menu', () => {
  it('offers shared and personal for manager roles', () => {
    expect(getChecklistCreateMenuOptions('manager').map((option) => option.id)).toEqual([
      'shared',
      'personal',
    ])
    expect(getChecklistCreateMenuOptions('owner').map((option) => option.id)).toEqual([
      'shared',
      'personal',
    ])
  })

  it('offers personal only for staff', () => {
    expect(getChecklistCreateMenuOptions('staff').map((option) => option.id)).toEqual(['personal'])
  })
})
