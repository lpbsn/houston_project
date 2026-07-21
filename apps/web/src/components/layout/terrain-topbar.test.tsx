// @vitest-environment jsdom

import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { TerrainTopbar } from './terrain-topbar'

describe('TerrainTopbar', () => {
  afterEach(() => {
    cleanup()
  })

  it('renders hub page title and trailing without logo', () => {
    const { container } = render(
      <TerrainTopbar
        variant="hub"
        pageTitle="Exécution"
        trailing={<button type="button">Notifications</button>}
      />,
    )

    expect(screen.getByRole('heading', { level: 1, name: 'Exécution' })).toBeTruthy()
    expect(screen.queryByRole('img', { name: 'Houston' })).toBeNull()
    expect(screen.getByRole('button', { name: 'Notifications' })).toBeTruthy()
    expect(container.querySelector('.grid-cols-\\[1fr_auto_1fr\\]')).toBeNull()
    expect(container.querySelector('.h-14')).toBeTruthy()
  })

  it('renders hub without page title using a spacer', () => {
    const { container } = render(<TerrainTopbar variant="hub" />)

    expect(screen.queryByRole('heading', { level: 1 })).toBeNull()
    expect(screen.queryByRole('img', { name: 'Houston' })).toBeNull()
    expect(container.querySelector('span[aria-hidden]')).toBeTruthy()
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
      <TerrainTopbar variant="detail" title="Observation" onBack={() => undefined} />,
    )

    const backButton = screen.getByRole('button', { name: 'Retour' })
    expect(backButton.className).toContain('border-0')
    expect(backButton.className).toContain('focus-visible:ring-0')
  })
})
