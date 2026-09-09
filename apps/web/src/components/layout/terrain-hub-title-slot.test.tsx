// @vitest-environment jsdom

import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { TerrainHubTitleSlot } from './terrain-hub-title-slot'
import { TerrainTopbar } from './terrain-topbar'

afterEach(() => {
  cleanup()
})

describe('TerrainHubTitleSlot', () => {
  it('clears the hub title slot on unmount', () => {
    const { rerender } = render(
      <>
        <TerrainTopbar variant="hub" pageTitle="Exécution" />
        <TerrainHubTitleSlot>
          <button type="button">Ma vue</button>
        </TerrainHubTitleSlot>
      </>,
    )

    expect(screen.getByRole('button', { name: 'Ma vue' })).toBeTruthy()

    rerender(<TerrainTopbar variant="hub" pageTitle="Exécution" />)

    expect(screen.queryByRole('button', { name: 'Ma vue' })).toBeNull()
  })

  it('clears the previous hub slot when the page slot is replaced', () => {
    const { rerender } = render(
      <>
        <TerrainTopbar variant="hub" pageTitle="Exécution" />
        <TerrainHubTitleSlot>
          <button type="button">Ma vue</button>
        </TerrainHubTitleSlot>
      </>,
    )

    rerender(
      <>
        <TerrainTopbar variant="hub" pageTitle="Observations" />
        <TerrainHubTitleSlot>
          <button type="button">Ma zone</button>
        </TerrainHubTitleSlot>
      </>,
    )

    expect(screen.queryByRole('button', { name: 'Ma vue' })).toBeNull()
    expect(screen.getByRole('button', { name: 'Ma zone' })).toBeTruthy()
  })
})
