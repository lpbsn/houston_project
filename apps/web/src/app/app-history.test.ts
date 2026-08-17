// @vitest-environment jsdom

import { afterEach, describe, expect, it, vi } from 'vitest'

import { createBrowserHistory, createMemoryHistory, getHrefSearch } from '@/app/app-history'

describe('getHrefSearch', () => {
  it('returns the query string including the leading question mark', () => {
    expect(getHrefSearch('/analytics?q=retard')).toBe('?q=retard')
  })

  it('strips the hash before reading search', () => {
    expect(getHrefSearch('/reporting?tab=comments#section')).toBe('?tab=comments')
  })

  it('returns an empty string when there is no query', () => {
    expect(getHrefSearch('/signals')).toBe('')
  })
})

describe('createMemoryHistory', () => {
  it('starts at the initial href and notifies subscribers on navigate', () => {
    const history = createMemoryHistory('/signals')
    const listener = vi.fn()
    const unsubscribe = history.subscribe(listener)

    expect(history.getHref()).toBe('/signals')

    history.navigate('/signals/sig-1')
    expect(history.getHref()).toBe('/signals/sig-1')
    expect(listener).toHaveBeenCalledTimes(1)

    history.navigate('/signals/sig-1?tab=comments', { replace: true })
    expect(history.getHref()).toBe('/signals/sig-1?tab=comments')
    expect(listener).toHaveBeenCalledTimes(2)

    unsubscribe()
    history.navigate('/chat')
    expect(listener).toHaveBeenCalledTimes(2)
  })

  it('does not notify when navigating to the same href', () => {
    const history = createMemoryHistory('/login')
    const listener = vi.fn()
    history.subscribe(listener)

    history.navigate('/login')
    expect(listener).not.toHaveBeenCalled()
  })
})

describe('createBrowserHistory', () => {
  afterEach(() => {
    window.history.replaceState(null, '', '/')
  })

  it('updates the browser URL and notifies without waiting for popstate', () => {
    window.history.replaceState(null, '', '/reporting')
    const history = createBrowserHistory()
    const listener = vi.fn()
    history.subscribe(listener)

    history.navigate('/signals')
    expect(window.location.pathname).toBe('/signals')
    expect(history.getHref()).toBe('/signals')
    expect(listener).toHaveBeenCalledTimes(1)

    history.navigate('/signals?tab=comments', { replace: true })
    expect(window.location.search).toBe('?tab=comments')
    expect(listener).toHaveBeenCalledTimes(2)
  })

  it('notifies on popstate from the browser back control', () => {
    window.history.replaceState(null, '', '/reporting')
    const history = createBrowserHistory()
    const listener = vi.fn()
    history.subscribe(listener)

    window.history.pushState(null, '', '/chat')
    window.dispatchEvent(new PopStateEvent('popstate'))

    expect(history.getHref()).toBe('/chat')
    expect(listener).toHaveBeenCalledTimes(1)
  })
})
