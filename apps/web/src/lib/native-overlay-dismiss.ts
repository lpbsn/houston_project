const overlayDismissStack: Array<() => void> = []

export function registerNativeOverlayDismiss(dismiss: () => void): () => void {
  overlayDismissStack.push(dismiss)
  return () => {
    const index = overlayDismissStack.lastIndexOf(dismiss)
    if (index !== -1) {
      overlayDismissStack.splice(index, 1)
    }
  }
}

export function dismissTopNativeOverlay(): boolean {
  const dismiss = overlayDismissStack.pop()
  if (!dismiss) {
    return false
  }
  dismiss()
  return true
}

export function resetNativeOverlayDismissForTests() {
  overlayDismissStack.length = 0
}
