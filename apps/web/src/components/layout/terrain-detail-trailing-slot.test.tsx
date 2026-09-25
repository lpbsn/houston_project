// @vitest-environment jsdom

import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { TerrainDetailTrailingSlot } from './terrain-detail-trailing-slot'
import { TerrainTopbar } from './terrain-topbar'

afterEach(() => {
  cleanup()
})

describe('TerrainDetailTrailingSlot', () => {
  it('clears the detail trailing slot on unmount', () => {
    const { rerender } = render(
      <>
        <TerrainTopbar variant="detail" title="Plan d'action" hideTitle onBack={() => undefined} />
        <TerrainDetailTrailingSlot>
          <button type="button">Marquer terminé</button>
        </TerrainDetailTrailingSlot>
      </>,
    )

    expect(screen.getByRole('button', { name: 'Marquer terminé' })).toBeTruthy()
    expect(screen.queryByText("Plan d'action")).toBeNull()

    rerender(
      <TerrainTopbar variant="detail" title="Plan d'action" hideTitle onBack={() => undefined} />,
    )

    expect(screen.queryByRole('button', { name: 'Marquer terminé' })).toBeNull()
  })
})
