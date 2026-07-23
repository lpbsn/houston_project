// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ObservationProcessingBanner } from '@/features/observations/components/observation-processing-banner'

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

vi.mock('@/features/observations/components/observation-processing-tracker-provider', () => ({
  useObservationProcessingBannerView: () => ({
    kind: 'terminal',
    observationId: 'obs-1',
    label: 'Signal créé',
    interactive: true,
    navigateTo: '/signals/sig-1',
    createdCount: 1,
    updatedCount: 0,
    signalIds: ['sig-1'],
    status: 'processed',
    uxStatus: 'signal_created',
  }),
}))

describe('ObservationProcessingBanner', () => {
  afterEach(() => {
    cleanup()
  })

  it('keeps pointer-events-auto on the interactive root and navigates on click', () => {
    const navigate = vi.fn()
    render(createElement(ObservationProcessingBanner, { navigate }))

    const interactiveRoot = screen.getByText('Signal créé').closest('.pointer-events-auto')
    expect(interactiveRoot).toBeTruthy()

    fireEvent.click(screen.getByRole('status'))
    expect(navigate).toHaveBeenCalledWith('/signals/sig-1')
  })
})
