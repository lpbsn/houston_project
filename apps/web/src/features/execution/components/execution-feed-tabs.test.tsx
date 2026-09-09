// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ExecutionFeedTabs } from './execution-feed-tabs'

afterEach(() => {
  cleanup()
})

describe('ExecutionFeedTabs', () => {
  it('exposes a segmented tablist for view mode', () => {
    const onChange = vi.fn()
    render(<ExecutionFeedTabs viewMode="personal" onChange={onChange} />)

    expect(screen.getByRole('tablist', { name: 'Mode de vue' })).toBeTruthy()
    expect(screen.getByRole('tab', { name: 'Ma vue' }).getAttribute('aria-selected')).toBe('true')
    expect(screen.getByRole('tab', { name: 'Vue globale' }).getAttribute('aria-selected')).toBe('false')
  })

  it('calls onChange when a tab is clicked', () => {
    const onChange = vi.fn()
    render(<ExecutionFeedTabs viewMode="personal" onChange={onChange} />)

    fireEvent.click(screen.getByRole('tab', { name: 'Vue globale' }))

    expect(onChange).toHaveBeenCalledWith('general')
  })
})
