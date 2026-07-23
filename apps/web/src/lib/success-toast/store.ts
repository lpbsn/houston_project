import {
  SUCCESS_TOAST_MAX_VISIBLE,
  SUCCESS_TOAST_TTL_MS,
  type NotifySuccessInput,
  type SuccessToast,
} from './types'

type Listener = () => void

const listeners = new Set<Listener>()
const dismissTimers = new Map<string, ReturnType<typeof setTimeout>>()

let toasts: SuccessToast[] = []
let nextId = 0

function emit(): void {
  for (const listener of listeners) {
    listener()
  }
}

function clearDismissTimer(id: string): void {
  const timer = dismissTimers.get(id)
  if (timer !== undefined) {
    clearTimeout(timer)
    dismissTimers.delete(id)
  }
}

function scheduleDismiss(id: string): void {
  clearDismissTimer(id)
  const timer = setTimeout(() => {
    dismissTimers.delete(id)
    dismissSuccessToast(id)
  }, SUCCESS_TOAST_TTL_MS)
  dismissTimers.set(id, timer)
}

function setToasts(next: SuccessToast[]): void {
  toasts = next
  emit()
}

export function subscribeSuccessToasts(listener: Listener): () => void {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

export function getSuccessToastsSnapshot(): SuccessToast[] {
  return toasts
}

export function notifySuccess(input: NotifySuccessInput): string {
  const id = `success-toast-${++nextId}`
  const toast: SuccessToast = {
    id,
    message: input.message,
    kind: input.kind,
  }

  let next = [...toasts, toast]
  const overflow = next.length - SUCCESS_TOAST_MAX_VISIBLE
  if (overflow > 0) {
    const evicted = next.slice(0, overflow)
    for (const item of evicted) {
      clearDismissTimer(item.id)
    }
    next = next.slice(overflow)
  }

  setToasts(next)
  scheduleDismiss(id)
  return id
}

export function dismissSuccessToast(id: string): void {
  clearDismissTimer(id)
  if (!toasts.some((toast) => toast.id === id)) {
    return
  }
  setToasts(toasts.filter((toast) => toast.id !== id))
}

/** Clears all toasts and timers with a single emit (auth/tenant boundaries). */
export function clearSuccessToasts(): void {
  for (const id of dismissTimers.keys()) {
    clearDismissTimer(id)
  }
  toasts = []
  emit()
}

/** Test helper — clears toasts/timers and resets id counter. */
export function resetSuccessToastsForTests(): void {
  clearSuccessToasts()
  nextId = 0
}
