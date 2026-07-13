// @vitest-environment jsdom

import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { TerrainTopbar } from './terrain-topbar'

describe('TerrainTopbar', () => {
  afterEach(() => {
    cleanup()
  })

  it('renders hub page title, logo, and trailing', () => {
    render(
      <TerrainTopbar
        variant="hub"
        pageTitle="Exécution"
        trailing={<button type="button">Notifications</button>}
      />,
    )

    expect(screen.getByRole('heading', { level: 1, name: 'Exécution' })).toBeTruthy()
    expect(screen.getByRole('img', { name: 'Houston' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Notifications' })).toBeTruthy()
  })

  it('renders hub without page title', () => {
    const { container } = render(<TerrainTopbar variant="hub" />)

    expect(screen.queryByRole('heading', { level: 1 })).toBeNull()
    expect(screen.getByRole('img', { name: 'Houston' })).toBeTruthy()
    expect(container.querySelector('span[aria-hidden]')).toBeTruthy()
  })

  it('renders compact hub with reduced height', () => {
    const { container } = render(<TerrainTopbar variant="hub" topbarSize="compact" />)

    expect(screen.queryByRole('heading', { level: 1 })).toBeNull()
    expect(container.querySelector('.h-14')).toBeTruthy()
  })

  it('renders long hub page titles without crashing', () => {
    render(
      <TerrainTopbar
        variant="hub"
        pageTitle="Page introuvable avec un titre très long qui doit être tronqué"
      />,
    )

    expect(
      screen.getByRole('heading', {
        level: 1,
        name: 'Page introuvable avec un titre très long qui doit être tronqué',
      }),
    ).toBeTruthy()
  })

  it('renders detail back button without visible border classes', () => {
    render(
      <TerrainTopbar variant="detail" title="Signal" onBack={() => undefined} />,
    )

    const backButton = screen.getByRole('button', { name: 'Retour' })
    expect(backButton.className).toContain('border-0')
    expect(backButton.className).toContain('focus-visible:ring-0')
  })
})
