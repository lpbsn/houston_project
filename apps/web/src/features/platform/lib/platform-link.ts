export function shouldHandlePlatformLinkClick(
  event: Pick<MouseEvent, 'button' | 'metaKey' | 'ctrlKey' | 'shiftKey' | 'altKey' | 'defaultPrevented'>,
): boolean {
  if (event.defaultPrevented) {
    return false
  }
  if (event.button !== 0) {
    return false
  }
  if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
    return false
  }
  return true
}
