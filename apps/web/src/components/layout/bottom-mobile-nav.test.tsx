// @vitest-environment jsdom
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { BottomMobileNav } from '@/components/layout/bottom-mobile-nav'

describe('BottomMobileNav', () => {
  afterEach(() => {
    cleanup()
  })

  it('renders above sticky page footers via z-index', () => {
    render(
      <BottomMobileNav
        activePath="/reporting"
        navigate={vi.fn()}
      />,
    )

    const nav = screen.getByRole('navigation', { name: 'Navigation terrain' })
    expect(nav.className).toContain('z-20')
    expect(nav.className).toContain('relative')
    expect(nav.className).toContain('pb-[max(0.25rem,var(--app-safe-bottom))]')
    expect(screen.getByRole('link', { name: 'Nouvelle observation' })).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Nouvelle observation' }).className).toContain(
      '114660',
    )
  })

  it('keeps safe area padding on nav and a fixed h-11 row on ul', () => {
    const { container } = render(
      <BottomMobileNav activePath="/signals" navigate={vi.fn()} />,
    )

    const nav = screen.getByRole('navigation', { name: 'Navigation terrain' })
    const list = container.querySelector('ul')

    expect(list?.className).toContain('h-11')
    expect(list?.className).not.toContain('pb-[max')
    expect(list?.className).not.toContain('pt-')
    expect(nav.className).toContain('pb-[max(0.25rem,var(--app-safe-bottom))]')
  })

  it('renders primary FAB as a 56x56 absolute link outside the row flow', () => {
    render(
      <BottomMobileNav activePath="/reporting" navigate={vi.fn()} />,
    )

    const primaryLink = screen.getByRole('link', { name: 'Nouvelle observation' })
    expect(primaryLink.className).toContain('absolute')
    expect(primaryLink.className).toContain('h-14')
    expect(primaryLink.className).toContain('w-14')
    expect(primaryLink.className).not.toContain('pointer-events-none')
  })

  it('renders standard tabs with 44x44 minimum touch targets', () => {
    render(
      <BottomMobileNav activePath="/signals" navigate={vi.fn()} />,
    )

    const signalsLink = screen.getByRole('link', { name: 'Observations' })
    expect(signalsLink.className).toContain('min-h-11')
    expect(signalsLink.className).toContain('min-w-11')
    expect(signalsLink.className).toContain('w-full')
    expect(signalsLink.className).not.toContain('min-w-0')
    expect(signalsLink.className).not.toContain('overflow-hidden')
  })

  it('contains non-FAB labels with full-width truncate in the column', () => {
    const { container } = render(
      <BottomMobileNav activePath="/signals" navigate={vi.fn()} />,
    )

    const signalsLink = screen.getByRole('link', { name: 'Observations' })
    const label = signalsLink.querySelector('span')
    const listItem = signalsLink.closest('li')
    const nav = screen.getByRole('navigation', { name: 'Navigation terrain' })
    const list = container.querySelector('ul')
    const fabItem = screen.getByRole('link', { name: 'Nouvelle observation' }).closest('li')

    expect(label?.className).toContain('w-full')
    expect(label?.className).toContain('truncate')
    expect(label?.className).toContain('text-center')
    expect(listItem?.className).not.toContain('overflow-hidden')
    expect(listItem?.className).not.toContain('min-w-0')
    expect(nav.className).not.toContain('overflow-hidden')
    expect(list?.className).not.toContain('overflow-hidden')
    expect(fabItem?.className).not.toContain('overflow-hidden')
  })

  it('uses five equal columns when Chat is visible', () => {
    const { container } = render(
      <BottomMobileNav activePath="/signals" navigate={vi.fn()} showChat />,
    )

    const list = container.querySelector('ul')
    expect(list?.style.gridTemplateColumns).toBe('repeat(5, minmax(0, 1fr))')
    expect(screen.getByRole('link', { name: 'Chat' })).toBeTruthy()
  })

  it('uses four equal columns when Chat is hidden', () => {
    const { container } = render(
      <BottomMobileNav activePath="/signals" navigate={vi.fn()} showChat={false} />,
    )

    const list = container.querySelector('ul')
    expect(list?.style.gridTemplateColumns).toBe('repeat(4, minmax(0, 1fr))')
    expect(screen.queryByRole('link', { name: 'Chat' })).toBeNull()
  })

  it('keeps Analytics out of the compact mobile nav', () => {
    render(
      <BottomMobileNav activePath="/signals" navigate={vi.fn()} />,
    )

    expect(screen.queryByRole('link', { name: 'Analyse' })).toBeNull()
  })

  it('can render every tab without a current page', () => {
    render(<BottomMobileNav navigate={vi.fn()} />)

    expect(screen.getByRole('navigation', { name: 'Navigation terrain' })).toBeTruthy()
    expect(screen.queryByRole('link', { current: 'page' })).toBeNull()
  })
})
