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

  it('keeps safe area padding on nav and a fixed h-12 row on ul', () => {
    const { container } = render(
      <BottomMobileNav activePath="/signals" navigate={vi.fn()} />,
    )

    const nav = screen.getByRole('navigation', { name: 'Navigation terrain' })
    const list = container.querySelector('ul')

    expect(list?.className).toContain('h-12')
    expect(list?.className).toContain('grid-cols-5')
    expect(list?.className).toContain('pl-[max(0.5rem,var(--app-safe-left))]')
    expect(list?.className).toContain('pr-[max(0.5rem,var(--app-safe-right))]')
    expect(list?.className).not.toContain('pb-[max')
    expect(list?.className).not.toContain('pt-')
    expect(nav.className).toContain('pb-[max(0.25rem,var(--app-safe-bottom))]')
  })

  it('renders primary FAB as a 56x56 absolute link outside the row flow', () => {
    render(
      <BottomMobileNav activePath="/reporting" navigate={vi.fn()} />,
    )

    const primaryLink = screen.getByRole('link', { name: 'Nouvelle observation' })
    const fabItem = primaryLink.closest('li')
    expect(primaryLink.className).toContain('absolute')
    expect(primaryLink.className).toContain('h-14')
    expect(primaryLink.className).toContain('w-14')
    expect(primaryLink.className).toContain('-translate-y-[calc(50%+0.5rem)]')
    expect(primaryLink.className).not.toContain('pointer-events-none')
    expect(fabItem?.className).toContain('relative')
    expect(fabItem?.className).toContain('h-11')
  })

  it('renders standard tabs with 48x48 minimum touch targets', () => {
    render(
      <BottomMobileNav activePath="/signals" navigate={vi.fn()} />,
    )

    const signalsLink = screen.getByRole('link', { name: 'Observations' })
    expect(signalsLink.className).toContain('min-h-12')
    expect(signalsLink.className).toContain('min-w-12')
    expect(signalsLink.className).toContain('w-full')
    expect(signalsLink.className).not.toContain('min-w-0')
    expect(signalsLink.className).not.toContain('overflow-hidden')
    expect(signalsLink.querySelector('svg')?.getAttribute('class')).toContain('h-5')
    expect(signalsLink.querySelector('svg')?.getAttribute('class')).toContain('w-5')
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

  it('always renders five equal columns including Chat', () => {
    const { container } = render(
      <BottomMobileNav activePath="/signals" navigate={vi.fn()} />,
    )

    const list = container.querySelector('ul')
    expect(list?.className).toContain('grid-cols-5')
    expect(screen.getByRole('link', { name: 'Chat' })).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Observations' })).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Exécution' })).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Nouvelle observation' })).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Général' })).toBeTruthy()
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
