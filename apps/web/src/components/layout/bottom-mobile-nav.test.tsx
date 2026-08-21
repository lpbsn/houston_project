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
