// @vitest-environment jsdom

import { createElement } from 'react'
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { SuccessToastHost } from '@/components/domain/success-toast-host'
import { notifySuccess, resetSuccessToastsForTests } from '@/lib/success-toast'

vi.mock('framer-motion', () => ({
  AnimatePresence: ({ children }: { children: React.ReactNode }) => children,
  motion: {
    div: ({
      children,
      className,
    }: {
      children: React.ReactNode
      className?: string
    }) => <div className={className}>{children}</div>,
  },
  useReducedMotion: () => true,
}))

describe('SuccessToastHost', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    resetSuccessToastsForTests()
  })

  afterEach(() => {
    resetSuccessToastsForTests()
    cleanup()
    vi.useRealTimers()
  })

  it('renders toast message with kind-mapped icon and dismisses manually', () => {
    render(createElement(SuccessToastHost))
    act(() => {
      notifySuccess({ message: 'Modèle supprimé.', kind: 'deleted' })
    })

    expect(screen.getByText('Modèle supprimé.')).toBeTruthy()
    expect(screen.getByRole('status').querySelector('[data-toast-kind="deleted"]')).toBeTruthy()

    const interactiveRoot = screen.getByText('Modèle supprimé.').closest('.pointer-events-auto')
    expect(interactiveRoot).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: 'Fermer' }))
    expect(screen.queryByRole('status')).toBeNull()
  })

  it('auto-dismisses after TTL', () => {
    render(createElement(SuccessToastHost))
    act(() => {
      notifySuccess({ message: 'Plan validé.', kind: 'validated' })
    })

    expect(screen.getByText('Plan validé.')).toBeTruthy()
    act(() => {
      vi.advanceTimersByTime(4000)
    })
    expect(screen.queryByText('Plan validé.')).toBeNull()
  })
})
