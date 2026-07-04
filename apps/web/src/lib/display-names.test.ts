import { describe, expect, it } from 'vitest'

import { getDisplayNameInitials } from './display-names'

describe('getDisplayNameInitials', () => {
  it('derives initials from short creator name', () => {
    expect(getDisplayNameInitials('Jean D.')).toBe('JD')
  })

  it('derives initials from full name', () => {
    expect(getDisplayNameInitials('Jean Dupont')).toBe('JD')
  })
})
