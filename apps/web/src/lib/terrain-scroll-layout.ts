const OVERFLOW_Y_SCROLL_CLASS_PATTERN = /overflow-y-(?:auto|scroll)/

export function hasOverflowYScrollClass(className: string): boolean {
  return OVERFLOW_Y_SCROLL_CLASS_PATTERN.test(className)
}

/** Collect elements with overflow-y-auto|scroll Tailwind classes within root. */
export function collectOverflowYScrollElements(root: ParentNode): HTMLElement[] {
  const results: HTMLElement[] = []
  root.querySelectorAll<HTMLElement>('*').forEach((element) => {
    if (hasOverflowYScrollClass(element.className)) {
      results.push(element)
    }
  })
  return results
}

export function expectSinglePageScrollZone(root: ParentNode): HTMLElement {
  const scrollZones = collectOverflowYScrollElements(root)
  if (scrollZones.length !== 1) {
    throw new Error(
      `Expected exactly 1 overflow-y scroll zone, found ${scrollZones.length}`,
    )
  }
  return scrollZones[0]!
}
