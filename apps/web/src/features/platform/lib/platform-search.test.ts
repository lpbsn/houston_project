import { describe, expect, it } from 'vitest'

import { readSearchParam, withSearchQuery } from './platform-search'

describe('platform search helpers', () => {
  it('keeps q on a resource path', () => {
    expect(withSearchQuery('/platform/organizations/org-1', 'acme')).toBe(
      '/platform/organizations/org-1?q=acme',
    )
  })

  it('omits empty q', () => {
    expect(withSearchQuery('/platform/users', '')).toBe('/platform/users')
  })

  it('reads q from an existing search string', () => {
    expect(readSearchParam('?q=acme', 'q')).toBe('acme')
    expect(readSearchParam('', 'q')).toBe('')
  })
})
