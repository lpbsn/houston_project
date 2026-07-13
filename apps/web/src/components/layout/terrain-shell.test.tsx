// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { TerrainShell } from '@/components/layout/terrain-shell'

vi.mock('@/components/layout/network-status-banner', () => ({
  NetworkStatusBanner: () => null,
}))

vi.mock('@/features/realtime/components/operational-reconnect-banner', () => ({
  OperationalReconnectBanner: () => null,
}))

vi.mock('@/features/realtime/components/operational-realtime-provider', () => ({
  useOptionalOperationalRealtime: () => null,
}))

vi.mock('@/lib/network-status', () => ({
  useNetworkStatus: () => ({ isOnline: true }),
}))

vi.mock('framer-motion', () => ({
  AnimatePresence: ({ children }: { children: React.ReactNode }) => children,
  motion: {
    div: ({ children, className }: { children: React.ReactNode; className?: string }) => (
      <div className={className}>{children}</div>
    ),
  },
  useReducedMotion: () => true,
}))

function renderTerrainShell(mainScroll: 'auto' | 'hidden' = 'hidden') {
  return render(
    createElement(
      TerrainShell,
      {
        contentKey: 'test',
        topbar: <div data-testid="terrain-topbar">Topbar</div>,
        updateBanner: <div role="status">Update available</div>,
        showBottomNav: false,
        mainScroll,
        navigate: () => undefined,
      },
      <div data-testid="page-content">Page</div>,
    ),
  )
}

afterEach(() => {
  cleanup()
})

describe('TerrainShell', () => {
  it('locks main scroll when mainScroll is hidden', () => {
    renderTerrainShell('hidden')

    const main = screen.getByRole('main')
    expect(main.className).toContain('overflow-hidden')
    expect(main.className).not.toContain('overflow-y-auto')
  })

  it('allows main scroll when mainScroll is auto', () => {
    renderTerrainShell('auto')

    const main = screen.getByRole('main')
    expect(main.className).toContain('overflow-y-auto')
  })

  it('renders update banner inside the shell as a shrink-0 sibling before main', () => {
    const { container } = renderTerrainShell('hidden')

    const main = screen.getByRole('main')
    const shell = main.parentElement
    expect(shell?.className).toContain('h-dvh')
    expect(shell?.className).toContain('overflow-hidden')

    const updateBannerSlot = main.previousElementSibling
    expect(updateBannerSlot?.className).toContain('shrink-0')
    expect(updateBannerSlot?.textContent).not.toBe('')
    expect(container.querySelector('[role="status"]')).toBeTruthy()
  })
})
