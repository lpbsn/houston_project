// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { TerrainCollapsibleFeedSection } from './terrain-collapsible-feed-section'

afterEach(() => {
  cleanup()
})

describe('TerrainCollapsibleFeedSection', () => {
  it('shows ChevronUp and children when expanded', () => {
    render(
      <TerrainCollapsibleFeedSection
        label="En cours"
        count={2}
        dotVariant="teal"
        expanded
        onToggle={vi.fn()}
      >
        <p>Contenu section</p>
      </TerrainCollapsibleFeedSection>,
    )

    expect(screen.getByText('En cours · 2')).toBeTruthy()
    expect(screen.getByText('Contenu section')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Replier la section En cours' }).getAttribute('aria-expanded')).toBe('true')
    expect(document.querySelector('.lucide-chevron-up')).toBeTruthy()
    expect(document.querySelector('.lucide-chevron-down')).toBeNull()
  })

  it('shows ChevronDown and hides children when collapsed', () => {
    render(
      <TerrainCollapsibleFeedSection
        label="Terminés"
        count={1}
        dotVariant="success"
        expanded={false}
        onToggle={vi.fn()}
      >
        <p>Contenu masqué</p>
      </TerrainCollapsibleFeedSection>,
    )

    expect(screen.queryByText('Contenu masqué')).toBeNull()
    expect(screen.getByRole('button', { name: 'Déplier la section Terminés' }).getAttribute('aria-expanded')).toBe('false')
    expect(document.querySelector('.lucide-chevron-down')).toBeTruthy()
    expect(document.querySelector('.lucide-chevron-up')).toBeNull()
  })

  it('calls onToggle when header is clicked', () => {
    const onToggle = vi.fn()

    render(
      <TerrainCollapsibleFeedSection label="En cours" count={1} expanded onToggle={onToggle}>
        <p>Contenu</p>
      </TerrainCollapsibleFeedSection>,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Replier la section En cours' }))

    expect(onToggle).toHaveBeenCalledTimes(1)
  })
})
