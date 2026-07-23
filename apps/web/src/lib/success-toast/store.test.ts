import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import {
  clearSuccessToasts,
  dismissSuccessToast,
  getSuccessToastsSnapshot,
  notifySuccess,
  resetSuccessToastsForTests,
  subscribeSuccessToasts,
} from './store'
import { SUCCESS_TOAST_MAX_VISIBLE, SUCCESS_TOAST_TTL_MS } from './types'

describe('successToastStore', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    resetSuccessToastsForTests()
  })

  afterEach(() => {
    resetSuccessToastsForTests()
    vi.useRealTimers()
  })

  it('adds a toast with message and kind', () => {
    notifySuccess({ message: 'Plan mis à jour.', kind: 'updated' })

    expect(getSuccessToastsSnapshot()).toEqual([
      {
        id: expect.any(String),
        message: 'Plan mis à jour.',
        kind: 'updated',
      },
    ])
  })

  it('evicts oldest toasts when exceeding max visible', () => {
    notifySuccess({ message: 'one', kind: 'created' })
    notifySuccess({ message: 'two', kind: 'created' })
    notifySuccess({ message: 'three', kind: 'created' })
    notifySuccess({ message: 'four', kind: 'created' })

    const snapshot = getSuccessToastsSnapshot()
    expect(snapshot).toHaveLength(SUCCESS_TOAST_MAX_VISIBLE)
    expect(snapshot.map((toast) => toast.message)).toEqual(['two', 'three', 'four'])
  })

  it('dismisses a toast manually', () => {
    const id = notifySuccess({ message: 'Plan validé.', kind: 'validated' })
    dismissSuccessToast(id)
    expect(getSuccessToastsSnapshot()).toEqual([])
  })

  it('auto-dismisses after TTL', () => {
    notifySuccess({ message: 'Plan terminé.', kind: 'completed' })
    expect(getSuccessToastsSnapshot()).toHaveLength(1)

    vi.advanceTimersByTime(SUCCESS_TOAST_TTL_MS)
    expect(getSuccessToastsSnapshot()).toEqual([])
  })

  it('notifies subscribers on change', () => {
    const listener = vi.fn()
    const unsubscribe = subscribeSuccessToasts(listener)

    notifySuccess({ message: 'Modèle activé.', kind: 'activated' })
    expect(listener).toHaveBeenCalled()

    unsubscribe()
    listener.mockClear()
    notifySuccess({ message: 'Modèle désactivé.', kind: 'deactivated' })
    expect(listener).not.toHaveBeenCalled()
  })

  it('clearSuccessToasts empties the stack with a single emit and cancels TTL timers', () => {
    notifySuccess({ message: 'one', kind: 'created' })
    notifySuccess({ message: 'two', kind: 'updated' })
    notifySuccess({ message: 'three', kind: 'deleted' })

    const listener = vi.fn()
    const unsubscribe = subscribeSuccessToasts(listener)

    clearSuccessToasts()

    expect(getSuccessToastsSnapshot()).toEqual([])
    expect(listener).toHaveBeenCalledTimes(1)

    listener.mockClear()
    vi.advanceTimersByTime(SUCCESS_TOAST_TTL_MS)
    expect(listener).not.toHaveBeenCalled()
    expect(getSuccessToastsSnapshot()).toEqual([])

    unsubscribe()
  })
})
