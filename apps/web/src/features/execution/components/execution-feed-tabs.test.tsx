// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ExecutionFeedTabs } from './execution-feed-tabs'

afterEach(() => {
  cleanup()
})

describe('ExecutionFeedTabs', () => {
  it('applies brand active styling to the selected tab', () => {
    const onChange = vi.fn()
    render(<ExecutionFeedTabs viewMode="personal" onChange={onChange} />)

    const personalTab = screen.getByRole('button', { name: 'Ma vue' })
    const globalTab = screen.getByRole('button', { name: 'Vue globale' })

    expect(personalTab.className).toContain('uppercase')
    expect(personalTab.className).toContain('bg-[#114660]')
    expect(personalTab.className).toContain('border-[#114660]')
    expect(globalTab.className).not.toContain('bg-[#114660]')
  })

  it('calls onChange when a tab is clicked', () => {
    const onChange = vi.fn()
    render(<ExecutionFeedTabs viewMode="personal" onChange={onChange} />)

    fireEvent.click(screen.getByRole('button', { name: 'Vue globale' }))

    expect(onChange).toHaveBeenCalledWith('general')
  })
})
