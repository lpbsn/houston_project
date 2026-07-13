// @vitest-environment jsdom

import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import { TerrainShell } from './terrain-shell'

type TerrainLayoutSnapshot = {
  label: 'T0' | 'T1' | 'T2'
  scrollY: number
  scrollingElementScrollTop: number
  innerHeight: number
  visualViewportHeight: number | null
  visualViewportOffsetTop: number
  shellTop: number | null
  shellHeight: number | null
}

declare global {
  interface Window {
    __terrainLayoutSnapshot?: (label: 'T0' | 'T1' | 'T2') => TerrainLayoutSnapshot
  }
}

describe('TerrainShell document scroll containment', () => {
  beforeEach(() => {
    delete document.documentElement.dataset.terrainShell
  })

  afterEach(() => {
    cleanup()
    delete document.documentElement.dataset.terrainShell
  })

  function renderShell() {
    return render(
      <TerrainShell
        contentKey="test"
        topbar={<header>Topbar</header>}
        showBottomNav={false}
        navigate={() => {}}
      >
        <textarea aria-label="Message" />
      </TerrainShell>,
    )
  }

  it('sets terrain shell dataset on mount and removes it on unmount', () => {
    const view = renderShell()

    expect(document.documentElement.dataset.terrainShell).toBe('')

    view.unmount()

    expect(document.documentElement.dataset.terrainShell).toBeUndefined()
  })

  it('marks the shell root for layout snapshots', () => {
    renderShell()

    expect(screen.getByLabelText('Message').closest('[data-terrain-shell-root]')).toBeTruthy()
  })

  it('exposes a dev-only snapshot helper while mounted', () => {
    const view = renderShell()

    expect(window.__terrainLayoutSnapshot).toBeTypeOf('function')
    const snapshot = window.__terrainLayoutSnapshot?.('T0')
    expect(snapshot).toMatchObject({
      label: 'T0',
      scrollY: expect.any(Number),
      scrollingElementScrollTop: expect.any(Number),
      innerHeight: expect.any(Number),
      visualViewportOffsetTop: expect.any(Number),
      shellTop: expect.anything(),
      shellHeight: expect.anything(),
    })
    expect(
      snapshot?.visualViewportHeight === null ||
        typeof snapshot?.visualViewportHeight === 'number',
    ).toBe(true)

    view.unmount()

    expect(window.__terrainLayoutSnapshot).toBeUndefined()
  })
})
