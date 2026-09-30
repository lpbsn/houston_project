import { dismissTopNativeOverlay } from '@/lib/native-overlay-dismiss'

export type NavigationLineage = {
  parentHref: string
  depth: number
}

/** How a history change should affect the current entry and its provenance. */
export type NavigationIntent = 'forward' | 'primary' | 'local' | 'system'

export type NavigateOptions = {
  replace?: boolean
  intent?: NavigationIntent
}

export type NavigationCause = 'pop' | 'programmatic'

export type AppHistory = {
  getHref(): string
  getLineage(): NavigationLineage | null
  getNavigationCause(): NavigationCause
  subscribe(listener: () => void): () => void
  navigate(href: string, options?: NavigateOptions): void
  /** Pop one entry when the browser stack can. Returns false when already at the root. */
  back(): boolean
}

export function getHrefSearch(href: string): string {
  const withoutHash = href.split('#')[0] ?? href
  const queryIndex = withoutHash.indexOf('?')
  return queryIndex === -1 ? '' : withoutHash.slice(queryIndex)
}

export function getHrefHash(href: string): string {
  const hashIndex = href.indexOf('#')
  if (hashIndex === -1) {
    return ''
  }
  return href.slice(hashIndex + 1)
}

export function pathnameOfHref(href: string): string {
  const withoutHash = href.split('#')[0] ?? href
  const withoutQuery = withoutHash.split('?')[0] ?? withoutHash
  return withoutQuery.replace(/\/+$/, '') || '/'
}

function readLineage(state: unknown): NavigationLineage | null {
  if (!state || typeof state !== 'object') {
    return null
  }
  const record = state as { parentHref?: unknown; depth?: unknown }
  if (typeof record.parentHref !== 'string' || typeof record.depth !== 'number' || record.depth < 1) {
    return null
  }
  return { parentHref: record.parentHref, depth: record.depth }
}

function resolveIntent(currentHref: string, href: string, options?: NavigateOptions): NavigationIntent {
  if (options?.intent) {
    return options.intent
  }
  if (options?.replace) {
    return pathnameOfHref(currentHref) === pathnameOfHref(href) ? 'local' : 'system'
  }
  return 'forward'
}

type HistoryEntry = {
  href: string
  lineage: NavigationLineage | null
}

type PrimaryTraversal = {
  href: string
  /**
   * `traverse` waits for the popstate from `go`.
   * `truncate` ignores the same-URL back that drops the forward stack.
   * `late` catches that go popstate if it arrives after the unmoved fallback.
   */
  phase: 'traverse' | 'truncate' | 'late'
  /** After the same-URL back, keep waiting for a go() popstate that has not arrived yet. */
  awaitLatePop?: boolean
}

/** Long enough for a queued history traversal to fire before we treat go() as a no-op. */
const PRIMARY_TRAVERSAL_WAIT_MS = 300

/**
 * Primary navigation must not leave the abandoned branch reachable by Back or
 * Forward, and must not render an intermediate hub. The History API can only
 * replace the current entry or traverse; it cannot delete entries below the
 * current one. Memory history applies that result in one step. Browser history
 * waits for the one popstate from `go(-depth)`, replaces that landed entry,
 * then push/back to drop whatever is now forward. If that popstate never
 * comes, the current entry becomes the destination so the click is not lost,
 * and a later popstate from the same go() is still internal.
 */
export function createBrowserHistory(): AppHistory {
  const listeners = new Set<() => void>()
  let cause: NavigationCause = 'programmatic'
  let primaryTraversal: PrimaryTraversal | null = null
  let primaryTimer: ReturnType<typeof setTimeout> | null = null
  let trackedHref = readBrowserHref()
  let trackedLineage = readLineage(window.history.state)

  function notify(nextCause: NavigationCause): void {
    cause = nextCause
    for (const listener of listeners) {
      listener()
    }
  }

  function getHref(): string {
    return readBrowserHref()
  }

  function getLineage(): NavigationLineage | null {
    return readLineage(window.history.state)
  }

  function subscribe(listener: () => void): () => void {
    listeners.add(listener)
    if (listeners.size === 1) {
      window.addEventListener('popstate', onPopState)
    }

    return () => {
      listeners.delete(listener)
      if (listeners.size === 0) {
        window.removeEventListener('popstate', onPopState)
      }
    }
  }

  function remember(href: string, lineage: NavigationLineage | null): void {
    trackedHref = href
    trackedLineage = lineage
  }

  function replaceEntry(href: string, lineage: NavigationLineage | null): void {
    window.history.replaceState(lineage, '', href)
    remember(href, lineage)
  }

  function clearPrimaryTimer(): void {
    if (primaryTimer !== null) {
      clearTimeout(primaryTimer)
      primaryTimer = null
    }
  }

  function armPrimaryTimer(delay: number, run: () => void): void {
    clearPrimaryTimer()
    primaryTimer = setTimeout(() => {
      primaryTimer = null
      run()
    }, delay)
  }

  function discardForwardEntries(href: string): void {
    const awaitLatePop = primaryTraversal?.phase === 'late'
    primaryTraversal = { href, phase: 'truncate', awaitLatePop }
    window.history.pushState(null, '', href)
    window.history.back()
    armPrimaryTimer(PRIMARY_TRAVERSAL_WAIT_MS, () => {
      if (primaryTraversal?.phase !== 'truncate' || primaryTraversal.href !== href) {
        return
      }
      settleTruncate(href, awaitLatePop)
    })
  }

  function settleTruncate(href: string, awaitLatePop: boolean): void {
    primaryTraversal = null
    remember(readBrowserHref(), readLineage(window.history.state))
    if (getHref() !== href) {
      notify('pop')
      return
    }
    if (!awaitLatePop) {
      return
    }
    primaryTraversal = { href, phase: 'late' }
    armPrimaryTimer(PRIMARY_TRAVERSAL_WAIT_MS, () => {
      if (primaryTraversal?.phase === 'late' && primaryTraversal.href === href) {
        primaryTraversal = null
      }
    })
  }

  function onPopState(): void {
    if (primaryTraversal?.phase === 'truncate') {
      const href = primaryTraversal.href
      const awaitLatePop = primaryTraversal.awaitLatePop === true
      clearPrimaryTimer()
      settleTruncate(href, awaitLatePop)
      return
    }
    if (primaryTraversal?.phase === 'late') {
      const href = primaryTraversal.href
      clearPrimaryTimer()
      primaryTraversal = null
      if (getHref() === href) {
        remember(readBrowserHref(), readLineage(window.history.state))
        return
      }
      replaceEntry(href, null)
      discardForwardEntries(href)
      notify('programmatic')
      return
    }
    if (primaryTraversal?.phase === 'traverse') {
      const href = primaryTraversal.href
      clearPrimaryTimer()
      primaryTraversal = null
      replaceEntry(href, null)
      discardForwardEntries(href)
      notify('programmatic')
      return
    }
    // Browser chrome back does not pass through performTerrainBack. Consume the
    // same overlay stack, then put the current entry back so the page under the
    // sheet never becomes active.
    if (dismissTopNativeOverlay()) {
      window.history.pushState(trackedLineage, '', trackedHref)
      return
    }
    remember(readBrowserHref(), readLineage(window.history.state))
    notify('pop')
  }

  function navigate(href: string, options?: NavigateOptions): void {
    const intent = resolveIntent(getHref(), href, options)
    if (getHref() === href) {
      return
    }

    clearPrimaryTimer()
    primaryTraversal = null

    if (intent === 'local') {
      replaceEntry(href, getLineage())
      notify('programmatic')
      return
    }

    if (intent === 'system') {
      replaceEntry(href, null)
      notify('programmatic')
      return
    }

    if (intent === 'primary') {
      const depth = getLineage()?.depth ?? 0
      if (depth <= 0) {
        replaceEntry(href, null)
        discardForwardEntries(href)
        notify('programmatic')
        return
      }
      const hrefBefore = getHref()
      primaryTraversal = { href, phase: 'traverse' }
      window.history.go(-depth)
      armPrimaryTimer(PRIMARY_TRAVERSAL_WAIT_MS, () => {
        if (primaryTraversal?.phase !== 'traverse' || primaryTraversal.href !== href) {
          return
        }
        if (getHref() !== hrefBefore) {
          return
        }
        primaryTraversal = { href, phase: 'late' }
        replaceEntry(href, null)
        discardForwardEntries(href)
        notify('programmatic')
      })
      return
    }

    const lineage: NavigationLineage = {
      parentHref: getHref(),
      depth: (getLineage()?.depth ?? 0) + 1,
    }
    window.history.pushState(lineage, '', href)
    remember(href, lineage)
    notify('programmatic')
  }

  function back(): boolean {
    window.history.back()
    return true
  }

  return {
    getHref,
    getLineage,
    getNavigationCause: () => cause,
    subscribe,
    navigate,
    back,
  }
}

export function createMemoryHistory(initialHref = '/'): AppHistory {
  const listeners = new Set<() => void>()
  let entries: HistoryEntry[] = [{ href: initialHref, lineage: null }]
  let index = 0
  let cause: NavigationCause = 'programmatic'

  function notify(nextCause: NavigationCause): void {
    cause = nextCause
    for (const listener of listeners) {
      listener()
    }
  }

  function current(): HistoryEntry {
    return entries[index] ?? entries[0]
  }

  function getHref(): string {
    return current().href
  }

  function subscribe(listener: () => void): () => void {
    listeners.add(listener)
    return () => {
      listeners.delete(listener)
    }
  }

  function navigate(href: string, options?: NavigateOptions): void {
    const intent = resolveIntent(getHref(), href, options)
    if (getHref() === href) {
      return
    }

    if (intent === 'local') {
      entries[index] = { href, lineage: current().lineage }
      entries = entries.slice(0, index + 1)
      notify('programmatic')
      return
    }

    if (intent === 'system' || intent === 'primary') {
      const depth = intent === 'primary' ? (current().lineage?.depth ?? 0) : 0
      index = Math.max(0, index - depth)
      entries[index] = { href, lineage: null }
      entries = entries.slice(0, index + 1)
      notify('programmatic')
      return
    }

    const lineage: NavigationLineage = {
      parentHref: getHref(),
      depth: (current().lineage?.depth ?? 0) + 1,
    }
    entries = entries.slice(0, index + 1)
    entries.push({ href, lineage })
    index += 1
    notify('programmatic')
  }

  function back(): boolean {
    if (index <= 0) {
      return false
    }
    index -= 1
    notify('pop')
    return true
  }

  return {
    getHref,
    getLineage: () => current().lineage,
    getNavigationCause: () => cause,
    subscribe,
    navigate,
    back,
  }
}

function readBrowserHref(): string {
  return `${window.location.pathname}${window.location.search}${window.location.hash}`
}
