// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { SignalViewMode } from '../types'
import { SignalFeedTabs } from './signal-feed-tabs'

const onChange = vi.fn()

beforeEach(() => {
  vi.clearAllMocks()
})

afterEach(() => {
  cleanup()
})

describe('SignalFeedTabs', () => {
  it('renders Ma zone and Vue globale as segmented tabs', () => {
    render(<SignalFeedTabs viewMode="personal" onChange={onChange} />)

    expect(screen.getByRole('tablist', { name: 'Mode de vue' })).toBeTruthy()
    expect(screen.getByRole('tab', { name: 'Ma zone' }).getAttribute('aria-selected')).toBe('true')
    expect(screen.getByRole('tab', { name: 'Vue globale' }).getAttribute('aria-selected')).toBe('false')
  })

  it('calls onChange when switching tabs', () => {
    const { rerender } = render(<SignalFeedTabs viewMode="personal" onChange={onChange} />)

    fireEvent.click(screen.getByRole('tab', { name: 'Vue globale' }))
    expect(onChange).toHaveBeenCalledWith('general' satisfies SignalViewMode)

    rerender(<SignalFeedTabs viewMode="general" onChange={onChange} />)
    fireEvent.click(screen.getByRole('tab', { name: 'Ma zone' }))
    expect(onChange).toHaveBeenCalledWith('personal' satisfies SignalViewMode)
  })
})
