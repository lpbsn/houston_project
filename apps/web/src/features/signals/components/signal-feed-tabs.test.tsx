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
  it('renders Ma zone and Vue globale labels', () => {
    render(<SignalFeedTabs viewMode="personal" onChange={onChange} />)

    expect(screen.getByRole('button', { name: /ma zone/i })).toBeTruthy()
    expect(screen.getByRole('button', { name: /vue globale/i })).toBeTruthy()
  })

  it('calls onChange when switching tabs', () => {
    const { rerender } = render(<SignalFeedTabs viewMode="personal" onChange={onChange} />)

    fireEvent.click(screen.getByRole('button', { name: /vue globale/i }))
    expect(onChange).toHaveBeenCalledWith('general' satisfies SignalViewMode)

    rerender(<SignalFeedTabs viewMode="general" onChange={onChange} />)
    fireEvent.click(screen.getByRole('button', { name: /ma zone/i }))
    expect(onChange).toHaveBeenCalledWith('personal' satisfies SignalViewMode)
  })
})
