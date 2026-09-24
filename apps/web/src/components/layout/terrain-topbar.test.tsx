// @vitest-environment jsdom

import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { TerrainTopbar } from './terrain-topbar'

function stubLgViewport(matches: boolean) {
  Object.defineProperty(window, 'matchMedia', {
    configurable: true,
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  })
}

describe('TerrainTopbar', () => {
  afterEach(() => {
    cleanup()
    vi.unstubAllEnvs()
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
    expect(container.querySelector('.min-h-14')).toBeTruthy()
  })

  it('renders hub without page title using a spacer', () => {
    const { container } = render(<TerrainTopbar variant="hub" />)

    expect(screen.queryByRole('heading', { level: 1 })).toBeNull()
    expect(screen.queryByRole('img', { name: 'Houston' })).toBeNull()
    expect(container.querySelector('span[aria-hidden]')).toBeTruthy()
    expect(container.querySelector('.min-h-14')).toBeTruthy()
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

  it('renders afterTitle beside the hub title and keeps trailing notifications', () => {
    render(
      <TerrainTopbar
        variant="hub"
        pageTitle="Exécution"
        afterTitle={<button type="button">Ma vue</button>}
        trailing={<button type="button">Notifications</button>}
      />,
    )

    const title = screen.getByRole('heading', { level: 1, name: 'Exécution' })
    const scope = screen.getByRole('button', { name: 'Ma vue' })
    const notifications = screen.getByRole('button', { name: 'Notifications' })
    expect(title.compareDocumentPosition(scope) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(scope.compareDocumentPosition(notifications) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  })

  it('renders detail back button without visible border classes', () => {
    render(
      <TerrainTopbar variant="detail" title="Observation" onBack={() => undefined} />,
    )

    const backButton = screen.getByRole('button', { name: 'Retour' })
    expect(backButton.className).toContain('border-0')
    expect(backButton.className).toContain('focus-visible:ring-0')
  })

  it('applies desktop height, padding and alignment only on desktop web', () => {
    stubLgViewport(true)
    const { unmount } = render(<TerrainTopbar variant="hub" pageTitle="Observations" />)
    const hubRow = screen.getByRole('banner').firstElementChild
    expect(hubRow?.className).toContain('lg:min-h-16')
    expect(hubRow?.className).toContain('lg:px-6')
    unmount()

    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    stubLgViewport(true)
    const nativeHub = render(<TerrainTopbar variant="hub" pageTitle="Observations" />)
    const nativeHubRow = screen.getByRole('banner').firstElementChild
    expect(nativeHubRow?.className).not.toContain('lg:min-h-16')
    expect(nativeHubRow?.className).not.toContain('lg:px-6')
    expect(screen.getByRole('banner').className).toContain('pt-[max(0.75rem,var(--app-safe-top))]')
    expect(screen.getByRole('banner').className).not.toContain('pt-0')
    nativeHub.unmount()

    const nativeDetail = render(
      <TerrainTopbar variant="detail" title="Observation" onBack={() => undefined} />,
    )
    const detailRow = screen.getByRole('banner').firstElementChild
    expect(detailRow?.className).not.toContain('lg:h-16')
    expect(detailRow?.className).not.toContain('lg:px-6')
    nativeDetail.unmount()

    render(
      <TerrainTopbar
        variant="detail"
        detailTitleLayout="belowBack"
        title="Plan d'action"
        onBack={() => undefined}
      />,
    )
    const belowBack = screen.getByRole('banner').firstElementChild
    expect(belowBack?.className).not.toContain('lg:px-6')
    expect(belowBack?.firstElementChild?.className).not.toContain('lg:min-h-16')
    expect(belowBack?.firstElementChild?.className).not.toContain('lg:items-center')
  })
})
