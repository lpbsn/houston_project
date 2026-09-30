// @vitest-environment jsdom

import { afterEach, describe, expect, it, vi } from 'vitest'

import { createBrowserHistory, createMemoryHistory, getHrefHash, getHrefSearch } from '@/app/app-history'
import {
  registerNativeOverlayDismiss,
  resetNativeOverlayDismissForTests,
} from '@/lib/native-overlay-dismiss'

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

describe('getHrefHash', () => {
  it('returns the fragment without the leading hash', () => {
    expect(getHrefHash('/invitations#invite-token')).toBe('invite-token')
  })

  it('returns an empty string when there is no fragment', () => {
    expect(getHrefHash('/invitations')).toBe('')
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

  it('keeps provenance on a local replace and clears it on a system replace', () => {
    const history = createMemoryHistory('/signals')
    history.navigate('/signals/sig-1')
    history.navigate('/signals/sig-1?tab=comments', { replace: true })

    expect(history.getHref()).toBe('/signals/sig-1?tab=comments')
    expect(history.getLineage()).toEqual({ parentHref: '/signals', depth: 1 })

    history.navigate('/login', { replace: true })
    expect(history.getHref()).toBe('/login')
    expect(history.getLineage()).toBeNull()
  })

  it('collapses a hierarchical branch on primary navigation without exposing the parent', () => {
    const history = createMemoryHistory('/signals')
    const seen: string[] = []
    history.subscribe(() => {
      seen.push(history.getHref())
    })

    history.navigate('/signals/sig-1')
    history.navigate('/signals/sig-1/plan')
    history.navigate('/execution', { intent: 'primary' })

    expect(seen).toEqual(['/signals/sig-1', '/signals/sig-1/plan', '/execution'])
    expect(history.getLineage()).toBeNull()
    expect(history.back()).toBe(false)
    expect(history.getHref()).toBe('/execution')
  })

  it('does not stack successive primary destinations', () => {
    const history = createMemoryHistory('/signals')
    history.navigate('/execution', { intent: 'primary' })
    history.navigate('/chat', { intent: 'primary' })

    expect(history.getHref()).toBe('/chat')
    expect(history.back()).toBe(false)
    expect(history.getHref()).toBe('/chat')
  })
})

describe('createBrowserHistory', () => {
  const unsubscribers: Array<() => void> = []

  afterEach(() => {
    for (const unsubscribe of unsubscribers) {
      unsubscribe()
    }
    unsubscribers.length = 0
    vi.useRealTimers()
    vi.restoreAllMocks()
    resetNativeOverlayDismissForTests()
    window.history.replaceState(null, '', '/')
  })

  it('updates the browser URL and notifies without waiting for popstate', () => {
    window.history.replaceState(null, '', '/reporting')
    const history = createBrowserHistory()
    const listener = vi.fn()
    unsubscribers.push(history.subscribe(listener))

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
    unsubscribers.push(history.subscribe(listener))

    window.history.pushState(null, '', '/chat')
    window.dispatchEvent(new PopStateEvent('popstate'))

    expect(history.getHref()).toBe('/chat')
    expect(listener).toHaveBeenCalledTimes(1)
  })

  it('does not notify when navigating to the same href', () => {
    window.history.replaceState(null, '', '/reporting')
    const history = createBrowserHistory()
    const listener = vi.fn()
    unsubscribers.push(history.subscribe(listener))

    history.navigate('/reporting')
    expect(listener).not.toHaveBeenCalled()
  })

  function flushTraversal(): void {
    vi.runAllTimers()
  }

  it('replaces the hierarchical root in one notification when leaving for a primary destination', () => {
    vi.useFakeTimers()
    window.history.replaceState(null, '', '/signals')
    const history = createBrowserHistory()
    const seen: string[] = []
    unsubscribers.push(
      history.subscribe(() => {
        seen.push(history.getHref())
      }),
    )

    history.navigate('/signals/sig-1')
    history.navigate('/signals/sig-1/plan')
    seen.length = 0
    history.navigate('/chat', { intent: 'primary' })
    flushTraversal()

    expect(history.getHref()).toBe('/chat')
    expect(history.getLineage()).toBeNull()
    expect(history.getNavigationCause()).toBe('programmatic')
    expect(seen).toEqual(['/chat'])

    window.history.forward()
    flushTraversal()
    expect(history.getHref()).toBe('/chat')
    history.back()
    flushTraversal()
    expect(history.getHref()).toBe('/chat')
    expect(seen.filter((href) => href === '/signals' || href === '/signals/sig-1')).toEqual([])
  })

  it('drops an existing forward stack when a primary destination replaces the current hub', () => {
    vi.useFakeTimers()
    window.history.replaceState(null, '', '/signals')
    const history = createBrowserHistory()
    unsubscribers.push(history.subscribe(() => undefined))

    history.navigate('/signals/sig-1')
    window.history.back()
    flushTraversal()
    expect(history.getHref()).toBe('/signals')

    history.navigate('/execution', { intent: 'primary' })
    flushTraversal()
    expect(history.getHref()).toBe('/execution')
    expect(history.getLineage()).toBeNull()

    window.history.forward()
    flushTraversal()
    expect(history.getHref()).toBe('/execution')
    history.back()
    flushTraversal()
    expect(history.getHref()).toBe('/execution')
  })

  it('finishes a primary traversal when its popstate arrives late', () => {
    vi.useFakeTimers()
    window.history.replaceState(null, '', '/signals')
    const history = createBrowserHistory()
    const seen: string[] = []
    unsubscribers.push(
      history.subscribe(() => {
        seen.push(history.getHref())
      }),
    )
    history.navigate('/signals/sig-1')
    seen.length = 0

    history.navigate('/chat', { intent: 'primary' })
    expect(history.getHref()).toBe('/signals/sig-1')
    expect(seen).toEqual([])

    vi.advanceTimersByTime(10)

    expect(history.getHref()).toBe('/chat')
    expect(history.getNavigationCause()).toBe('programmatic')
    expect(seen).toEqual(['/chat'])

    window.history.forward()
    flushTraversal()
    history.back()
    flushTraversal()
    expect(history.getHref()).toBe('/chat')
    expect(seen.filter((href) => href === '/signals' || href === '/signals/sig-1')).toEqual([])
  })

  it('settles the primary destination when go() never emits popstate', () => {
    vi.useFakeTimers()
    window.history.replaceState(null, '', '/signals')
    const history = createBrowserHistory()
    const seen: string[] = []
    unsubscribers.push(
      history.subscribe(() => {
        seen.push(`${history.getNavigationCause()}:${history.getHref()}`)
      }),
    )
    history.navigate('/signals/sig-1')
    seen.length = 0

    const originalGo = window.history.go.bind(window.history)
    let skippedTraverse = false
    vi.spyOn(window.history, 'go').mockImplementation((delta) => {
      if (!skippedTraverse) {
        skippedTraverse = true
        return
      }
      originalGo(delta)
    })

    history.navigate('/chat', { intent: 'primary' })
    expect(history.getHref()).toBe('/signals/sig-1')
    flushTraversal()

    expect(history.getHref()).toBe('/chat')
    expect(history.getNavigationCause()).toBe('programmatic')
    expect(seen).toEqual(['programmatic:/chat'])

    window.history.pushState(null, '', '/elsewhere')
    window.dispatchEvent(new PopStateEvent('popstate'))
    expect(history.getHref()).toBe('/elsewhere')
    expect(history.getNavigationCause()).toBe('pop')
  })

  it('keeps browser back on the current entry while an overlay consumes it', () => {
    vi.useFakeTimers()
    window.history.replaceState(null, '', '/signals')
    const history = createBrowserHistory()
    const seen: string[] = []
    unsubscribers.push(
      history.subscribe(() => {
        seen.push(history.getHref())
      }),
    )
    history.navigate('/signals/sig-1')
    seen.length = 0

    registerNativeOverlayDismiss(() => false)
    window.history.back()
    vi.runAllTimers()
    window.history.back()
    vi.runAllTimers()

    expect(history.getHref()).toBe('/signals/sig-1')
    expect(seen).toEqual([])
  })

  it('closes a dismissible overlay on browser back without leaving the page', () => {
    vi.useFakeTimers()
    window.history.replaceState(null, '', '/signals')
    const history = createBrowserHistory()
    const seen: string[] = []
    unsubscribers.push(
      history.subscribe(() => {
        seen.push(history.getHref())
      }),
    )
    history.navigate('/signals/sig-1')
    seen.length = 0
    const dismiss = vi.fn()
    registerNativeOverlayDismiss(dismiss)

    window.history.back()
    vi.runAllTimers()

    expect(dismiss).toHaveBeenCalledTimes(1)
    expect(history.getHref()).toBe('/signals/sig-1')
    expect(seen).toEqual([])

    window.history.back()
    vi.runAllTimers()
    expect(history.getHref()).toBe('/signals')
    expect(seen).toEqual(['/signals'])
  })
})
