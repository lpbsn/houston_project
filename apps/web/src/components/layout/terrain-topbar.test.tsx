// @vitest-environment jsdom

import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { TerrainTopbar } from './terrain-topbar'

describe('TerrainTopbar', () => {
  afterEach(() => {
    cleanup()
  })

  it('renders hub page title, logo, and trailing on one row', () => {
    const { container } = render(
      <TerrainTopbar
        variant="hub"
        pageTitle="Exécution"
        trailing={<button type="button">Notifications</button>}
      />,
    )

    expect(screen.getByRole('heading', { level: 1, name: 'Exécution' })).toBeTruthy()
    expect(screen.getByRole('img', { name: 'Houston' }).className).toContain('h-20')
    expect(screen.getByRole('button', { name: 'Notifications' })).toBeTruthy()

    const row = container.querySelector('.grid.h-20')
    expect(row).not.toBeNull()
    expect(row?.className).toContain('grid-cols-[1fr_auto_1fr]')
    expect(row?.querySelector('h1')?.textContent).toBe('Exécution')
    expect(row?.querySelector('img[alt="Houston"]')).toBeTruthy()
  })

  it('renders hub without page title using a left spacer', () => {
    const { container } = render(<TerrainTopbar variant="hub" />)

    expect(screen.queryByRole('heading', { level: 1 })).toBeNull()
    expect(screen.getByRole('img', { name: 'Houston' }).className).toContain('h-20')

    const row = container.querySelector('.grid.h-20')
    expect(row?.querySelector('h1')).toBeNull()
    expect(row?.querySelector('span[aria-hidden]')).toBeTruthy()
  })

  it('truncates long hub page titles', () => {
    render(
      <TerrainTopbar
        variant="hub"
        pageTitle="Page introuvable avec un titre très long qui doit être tronqué"
      />,
    )

    const heading = screen.getByRole('heading', {
      level: 1,
      name: 'Page introuvable avec un titre très long qui doit être tronqué',
    })
    expect(heading.className).toContain('truncate')
    expect(heading.className).toContain('text-2xl')
  })
})
