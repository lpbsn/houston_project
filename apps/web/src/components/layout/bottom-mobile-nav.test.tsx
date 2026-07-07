// @vitest-environment jsdom
import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { BottomMobileNav } from '@/components/layout/bottom-mobile-nav'

describe('BottomMobileNav', () => {
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
  })
})
