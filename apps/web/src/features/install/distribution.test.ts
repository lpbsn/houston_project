import { describe, expect, it } from 'vitest'

import { resolveAndroidChoice } from './distribution'

const CLOSED_JOIN = 'https://play.google.com/apps/testing/app.spore'
const CLOSED_INSTALL = 'https://play.google.com/store/apps/details?id=app.spore'

describe('resolveAndroidChoice', () => {
  it('keeps the request form while distribution is closed, even if a store URL is set', () => {
    expect(resolveAndroidChoice('closed', CLOSED_INSTALL)).toEqual({ kind: 'request' })
    expect(resolveAndroidChoice('closed', '')).toEqual({ kind: 'request' })
  })

  it('links directly when public distribution has a URL', () => {
    expect(resolveAndroidChoice('public', ' https://play.google.com/store/apps/details?id=app.spore ')).toEqual({
      kind: 'store',
      href: 'https://play.google.com/store/apps/details?id=app.spore',
    })
  })

  it('stays unavailable when public distribution has no URL', () => {
    expect(resolveAndroidChoice('public', '   ')).toEqual({ kind: 'unavailable' })
  })

  it('does not treat the closed-testing URLs as a public store link', () => {
    expect(resolveAndroidChoice('closed', CLOSED_JOIN).kind).toBe('request')
  })
})
