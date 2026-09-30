const overlayDismissStack: Array<() => void | boolean> = []

export function registerNativeOverlayDismiss(dismiss: () => void | boolean): () => void {
  overlayDismissStack.push(dismiss)
  return () => {
    const index = overlayDismissStack.lastIndexOf(dismiss)
    if (index !== -1) {
      overlayDismissStack.splice(index, 1)
    }
  }
}

export function dismissTopNativeOverlay(): boolean {
  const dismiss = overlayDismissStack.at(-1)
  if (!dismiss) {
    return false
  }
  const closed = dismiss()
  if (closed === false) {
    return true
  }
  overlayDismissStack.pop()
  return true
}

export function resetNativeOverlayDismissForTests() {
  overlayDismissStack.length = 0
}
