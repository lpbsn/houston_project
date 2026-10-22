/**
 * Computer check for the web runtime.
 *
 * `(pointer: fine)` is the primary pointer. Requiring `(hover: hover)` in the
 * same query keeps phones, tablets, and stylus-first devices on the width
 * rule: they report a coarse pointer, or a fine pointer that cannot hover.
 * A mouse or trackpad reports both and stays on the desktop interface at any
 * window width.
 */
export const COMPUTER_POINTER_QUERY = '(pointer: fine) and (hover: hover)'

export function hasComputerPointer(): boolean {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
    return false
  }

  return window.matchMedia(COMPUTER_POINTER_QUERY).matches
}
