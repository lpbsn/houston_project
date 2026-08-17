export type AppHistory = {
  getHref(): string
  subscribe(listener: () => void): () => void
  navigate(href: string, options?: { replace?: boolean }): void
}

export function getHrefSearch(href: string): string {
  const withoutHash = href.split('#')[0] ?? href
  const queryIndex = withoutHash.indexOf('?')
  return queryIndex === -1 ? '' : withoutHash.slice(queryIndex)
}

function readBrowserHref(): string {
  return `${window.location.pathname}${window.location.search}${window.location.hash}`
}

export function createBrowserHistory(): AppHistory {
  const listeners = new Set<() => void>()

  function notify(): void {
    for (const listener of listeners) {
      listener()
    }
  }

  function getHref(): string {
    return readBrowserHref()
  }

  function subscribe(listener: () => void): () => void {
    listeners.add(listener)
    if (listeners.size === 1) {
      window.addEventListener('popstate', notify)
    }

    return () => {
      listeners.delete(listener)
      if (listeners.size === 0) {
        window.removeEventListener('popstate', notify)
      }
    }
  }

  function navigate(href: string, options?: { replace?: boolean }): void {
    if (getHref() === href) {
      return
    }

    const method = options?.replace ? 'replaceState' : 'pushState'
    window.history[method](null, '', href)
    notify()
  }

  return { getHref, subscribe, navigate }
}

export function createMemoryHistory(initialHref = '/'): AppHistory {
  let href = initialHref
  const listeners = new Set<() => void>()

  function notify(): void {
    for (const listener of listeners) {
      listener()
    }
  }

  function getHref(): string {
    return href
  }

  function subscribe(listener: () => void): () => void {
    listeners.add(listener)
    return () => {
      listeners.delete(listener)
    }
  }

  function navigate(nextHref: string): void {
    if (href === nextHref) {
      return
    }

    href = nextHref
    notify()
  }

  return { getHref, subscribe, navigate }
}
