export const ACTION_PLAN_FIELD_ATTR = 'data-action-plan-field'

export const ACTION_PLAN_SCROLL_RETRY_MAX_ATTEMPTS = 10

function prefersReducedMotion(): boolean {
  if (typeof window === 'undefined') {
    return false
  }
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

function findActionPlanFieldElement(
  fieldKey: string,
  root: ParentNode,
): HTMLElement | null {
  const nodes = Array.from(root.querySelectorAll<HTMLElement>(`[${ACTION_PLAN_FIELD_ATTR}]`))
  for (const node of nodes) {
    if (node.getAttribute(ACTION_PLAN_FIELD_ATTR) === fieldKey) {
      return node
    }
  }
  return null
}

/**
 * Resolve the first errored field in real DOM order within `root`
 * (after collapsed sections have been opened).
 */
export function resolveFirstActionPlanErrorFieldKey(
  fieldErrors: Record<string, string>,
  root: ParentNode = document,
): string | null {
  const errorKeys = new Set(Object.keys(fieldErrors))
  if (errorKeys.size === 0) {
    return null
  }

  const nodes = Array.from(root.querySelectorAll<HTMLElement>(`[${ACTION_PLAN_FIELD_ATTR}]`))
  for (const node of nodes) {
    const key = node.getAttribute(ACTION_PLAN_FIELD_ATTR)
    if (key && errorKeys.has(key)) {
      return key
    }
  }
  return null
}

export function scrollToActionPlanFieldError(
  fieldKey: string,
  options: { root?: ParentNode } = {},
): () => void {
  const root = options.root ?? document
  let cancelled = false
  let attempt = 0
  let rafId: number | null = null

  const cancel = () => {
    cancelled = true
    if (rafId !== null) {
      cancelAnimationFrame(rafId)
    }
  }

  const tryScroll = () => {
    if (cancelled) {
      return
    }

    const element = findActionPlanFieldElement(fieldKey, root)
    if (element) {
      element.scrollIntoView({
        block: 'center',
        behavior: prefersReducedMotion() ? 'auto' : 'smooth',
      })
      return
    }

    attempt += 1
    if (attempt >= ACTION_PLAN_SCROLL_RETRY_MAX_ATTEMPTS) {
      return
    }
    rafId = requestAnimationFrame(tryScroll)
  }

  rafId = requestAnimationFrame(tryScroll)
  return cancel
}

/**
 * After advanced sections open, find first error in DOM order and scroll to it.
 * Does not focus.
 */
export function guideToFirstActionPlanFieldError(
  fieldErrors: Record<string, string>,
  options: { root?: ParentNode } = {},
): () => void {
  const root = options.root ?? document
  let cancelled = false
  let attempt = 0
  let rafId: number | null = null
  let nestedCancel: (() => void) | null = null

  const cancel = () => {
    cancelled = true
    nestedCancel?.()
    if (rafId !== null) {
      cancelAnimationFrame(rafId)
    }
  }

  const tryGuide = () => {
    if (cancelled) {
      return
    }

    const firstKey = resolveFirstActionPlanErrorFieldKey(fieldErrors, root)
    if (firstKey) {
      nestedCancel = scrollToActionPlanFieldError(firstKey, { root })
      return
    }

    attempt += 1
    if (attempt >= ACTION_PLAN_SCROLL_RETRY_MAX_ATTEMPTS) {
      return
    }
    rafId = requestAnimationFrame(tryGuide)
  }

  rafId = requestAnimationFrame(tryGuide)
  return cancel
}
