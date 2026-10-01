// @vitest-environment jsdom

import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import {
  TerrainDetailTrailingEndSlot,
  TerrainDetailTrailingSlot,
} from './terrain-detail-trailing-slot'
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

  it('places the end slot to the right of the topbar trailing control', () => {
    render(
      <>
        <TerrainTopbar
          variant="detail"
          title="Exécution"
          hideTitle
          onBack={() => undefined}
          trailing={<button type="button">Modifier</button>}
        />
        <TerrainDetailTrailingSlot>
          <button type="button">Marquer terminé</button>
        </TerrainDetailTrailingSlot>
        <TerrainDetailTrailingEndSlot>
          <button type="button">Autres actions</button>
        </TerrainDetailTrailingEndSlot>
      </>,
    )

    const actions = screen.getByRole('button', { name: 'Marquer terminé' })
    const edit = screen.getByRole('button', { name: 'Modifier' })
    const menu = screen.getByRole('button', { name: 'Autres actions' })
    expect(actions.compareDocumentPosition(edit) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(edit.compareDocumentPosition(menu) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  })
})
