import { describe, expect, it, vi } from 'vitest'

import { parseAppRoute } from '@/app/app-routes'

import {
  applyAppOpenTarget,
  buildLoginRedirectHref,
  buildSelectEstablishmentRedirectHref,
  isPendingDestinationHref,
  isPublicAppOpenTarget,
  parseAppOpenTargetFromLocation,
  parseExternalAppUrl,
  parsePendingAppOpenFromSearch,
  resolveSelectEstablishmentHintTarget,
} from './app-open-target'

const PUBLIC_ORIGIN = 'https://app.example.test'

describe('parseExternalAppUrl', () => {
  it('accepts the exact public HTTPS origin and keeps product query params', () => {
    expect(
      parseExternalAppUrl(
        'https://app.example.test/signals/s1?tab=comments&commentId=c1&establishment_id=est-2',
        PUBLIC_ORIGIN,
      ),
    ).toEqual({
      href: '/signals/s1?tab=comments&commentId=c1',
      establishmentId: 'est-2',
    })
  })

  it('accepts invitation paths without an establishment hint', () => {
    expect(parseExternalAppUrl('https://app.example.test/invitations/token-abc', PUBLIC_ORIGIN)).toEqual({
      href: '/invitations/token-abc',
    })
  })

  it('rejects http, other origins, custom schemes, and unknown product paths', () => {
    expect(parseExternalAppUrl('http://app.example.test/signals/s1', PUBLIC_ORIGIN)).toBeNull()
    expect(parseExternalAppUrl('https://evil.example.test/signals/s1', PUBLIC_ORIGIN)).toBeNull()
    expect(parseExternalAppUrl('https://app.example.test:8443/signals/s1', PUBLIC_ORIGIN)).toBeNull()
    expect(parseExternalAppUrl('capacitor://localhost/signals/s1', PUBLIC_ORIGIN)).toBeNull()
    expect(parseExternalAppUrl('app.spore://signals/s1', PUBLIC_ORIGIN)).toBeNull()
    expect(parseExternalAppUrl('https://app.example.test/not-a-product', PUBLIC_ORIGIN)).toBeNull()
    expect(parseExternalAppUrl('https://app.example.test//evil', PUBLIC_ORIGIN)).toBeNull()
  })

  it('rejects a public origin that is not https', () => {
    expect(
      parseExternalAppUrl('https://app.example.test/signals/s1', 'http://app.example.test'),
    ).toBeNull()
  })
})

describe('pending destination href', () => {
  it('allowlists AppRoute product destinations and rejects open redirects', () => {
    expect(isPendingDestinationHref('/signals/s1?tab=comments')).toBe(true)
    expect(isPendingDestinationHref('/invitations/token')).toBe(false)
    expect(isPendingDestinationHref('/login')).toBe(false)
    expect(isPendingDestinationHref('/')).toBe(false)
    expect(isPendingDestinationHref('https://evil.example/signals/s1')).toBe(false)
    expect(isPendingDestinationHref('//evil.example')).toBe(false)
  })

  it('treats invitations as public opens', () => {
    expect(isPublicAppOpenTarget({ href: '/invitations/token-abc' })).toBe(true)
    expect(isPublicAppOpenTarget({ href: '/signals/s1' })).toBe(false)
  })
})

describe('parseAppOpenTargetFromLocation', () => {
  it('extracts establishment_id from the current search without leaving it on href', () => {
    expect(
      parseAppOpenTargetFromLocation(parseAppRoute('/signals/s1'), '?tab=comments&establishment_id=est-2'),
    ).toEqual({
      href: '/signals/s1?tab=comments',
      establishmentId: 'est-2',
    })
  })

  it('does not stash login, invitation, or public routes', () => {
    expect(parseAppOpenTargetFromLocation(parseAppRoute('/login'), '?next=/signals/s1')).toBeNull()
    expect(parseAppOpenTargetFromLocation(parseAppRoute('/invitations/token'), '')).toBeNull()
    expect(parseAppOpenTargetFromLocation(parseAppRoute('/'), '')).toBeNull()
  })
})

describe('login and select-establishment carry', () => {
  it('preserves next and establishment_id as sibling query params', () => {
    const target = {
      href: '/signals/s1?tab=comments&commentId=c1',
      establishmentId: 'est-2',
    }
    const loginHref = buildLoginRedirectHref(target)
    expect(loginHref.startsWith('/login?')).toBe(true)
    expect(parsePendingAppOpenFromSearch(loginHref.slice('/login'.length))).toEqual(target)

    const selectHref = buildSelectEstablishmentRedirectHref(target)
    expect(parsePendingAppOpenFromSearch(selectHref.slice('/select-establishment'.length))).toEqual(
      target,
    )
  })

  it('keeps next without a hint and ignores open-redirect next values', () => {
    expect(parsePendingAppOpenFromSearch('?next=/chat/c1')).toEqual({ href: '/chat/c1' })
    expect(parsePendingAppOpenFromSearch('?next=https://evil.example/signals/s1')).toBeNull()
    expect(parsePendingAppOpenFromSearch('?next=/invitations/token')).toBeNull()
  })
})

describe('applyAppOpenTarget', () => {
  it('switches when the hint differs then navigates the stripped href', async () => {
    const switchEstablishment = vi.fn(async () => undefined)
    const navigate = vi.fn()

    await applyAppOpenTarget(
      { href: '/signals/s1', establishmentId: 'est-2' },
      {
        getActiveEstablishmentId: () => 'est-1',
        switchEstablishment,
        navigate,
      },
    )

    expect(switchEstablishment).toHaveBeenCalledWith('est-2')
    expect(navigate).toHaveBeenCalledWith('/signals/s1', { replace: true })
  })

  it('does not switch when there is no hint', async () => {
    const switchEstablishment = vi.fn(async () => undefined)
    const navigate = vi.fn()

    await applyAppOpenTarget(
      { href: '/signals/s1' },
      {
        getActiveEstablishmentId: () => 'est-1',
        switchEstablishment,
        navigate,
      },
    )

    expect(switchEstablishment).not.toHaveBeenCalled()
    expect(navigate).toHaveBeenCalledWith('/signals/s1', { replace: true })
  })
})

describe('resolveSelectEstablishmentHintTarget', () => {
  const memberships = [{ establishment_id: 'est-2' }, { establishment_id: 'est-3' }]

  it('returns the pending dest when the user is a member of the hinted establishment', () => {
    expect(
      resolveSelectEstablishmentHintTarget('?next=/signals/s1&establishment_id=est-2', memberships),
    ).toEqual({ href: '/signals/s1', establishmentId: 'est-2' })
  })

  it('returns null when the hint is missing or not in memberships', () => {
    expect(resolveSelectEstablishmentHintTarget('?next=/signals/s1', memberships)).toBeNull()
    expect(
      resolveSelectEstablishmentHintTarget('?next=/signals/s1&establishment_id=est-9', memberships),
    ).toBeNull()
  })
})
