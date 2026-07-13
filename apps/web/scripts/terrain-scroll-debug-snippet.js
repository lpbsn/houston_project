/**
 * Phase 0 — Diagnostic scroll PWA (console mobile).
 * Copier-coller dans Safari Web Inspector / Eruda sur /chat, /reporting, /signals.
 * Indépendant des classes Tailwind.
 */
(function () {
  const bottomNav = document.querySelector('nav[aria-label="Navigation terrain"]')
  const shell = document.querySelector('[data-terrain-shell-root]') ?? bottomNav?.parentElement ?? null
  const main = shell?.querySelector(':scope > main') ?? null

  const isScrollableOverflow = (el) => {
    const oy = getComputedStyle(el).overflowY
    return oy === 'auto' || oy === 'scroll' || oy === 'overlay'
  }

  const scrollCandidates = main ? [...main.querySelectorAll('*')].filter(isScrollableOverflow) : []

  const measureEl = (name, el) =>
    el
      ? {
          name,
          scrollTop: el.scrollTop,
          scrollHeight: el.scrollHeight,
          clientHeight: el.clientHeight,
          overflowY: getComputedStyle(el).overflowY,
          canScroll: el.scrollHeight > el.clientHeight + 1,
        }
      : { name, missing: true }

  const rows = [
    measureEl('document.scrollingElement', document.scrollingElement),
    measureEl('html', document.documentElement),
    measureEl('body', document.body),
    measureEl('#root', document.getElementById('root')),
    measureEl('TerrainShell (nav.parent)', shell),
    measureEl('main (shell > main)', main),
    ...scrollCandidates.slice(0, 5).map((el, i) => measureEl(`scrollCandidate[${i}]`, el)),
  ]
  console.table(rows)

  const vv = window.visualViewport
  const shellRect = shell?.getBoundingClientRect()
  const navRect = bottomNav?.getBoundingClientRect()

  console.log({
    innerHeight: window.innerHeight,
    visualViewport: vv ? { height: vv.height, offsetTop: vv.offsetTop, scale: vv.scale } : null,
    shellRect: shellRect
      ? { top: shellRect.top, bottom: shellRect.bottom, height: shellRect.height }
      : null,
    navRect: navRect ? { top: navRect.top, bottom: navRect.bottom, height: navRect.height } : null,
    navGapFromViewportBottom: navRect ? window.innerHeight - navRect.bottom : null,
    standalone: window.matchMedia('(display-mode: standalone)').matches,
    docScrollTop: document.scrollingElement?.scrollTop,
  })

  const targets = [
    ['document', document],
    ['document.scrollingElement', document.scrollingElement],
    ['main', main],
    ...scrollCandidates.slice(0, 3).map((el, i) => [`scrollCandidate[${i}]`, el]),
  ].filter(([, el]) => el)

  window.__houstonScrollDebug = targets.map(([label, el]) => {
    const handler = () =>
      console.log('[scroll]', label, { scrollTop: el.scrollTop, ts: Date.now() })
    el.addEventListener('scroll', handler, { passive: true })
    return { label, el, handler }
  })

  console.log(
    'Scroll listeners actifs. Effectuer overscroll / scroll, puis:',
    'window.__houstonScrollDebug.forEach(({ el, handler }) => el.removeEventListener("scroll", handler))',
  )
})()
