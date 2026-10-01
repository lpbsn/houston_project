// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { TerrainDialog } from '@/components/ui/terrain/terrain-dialog'
import { resetNativeOverlayDismissForTests } from '@/lib/native-overlay-dismiss'

describe('TerrainDialog', () => {
  afterEach(() => {
    cleanup()
    resetNativeOverlayDismissForTests()
  })

  it('closes from the scrim and Escape, and exposes testId on the dialog', () => {
    const onClose = vi.fn()
    const { container } = render(
      <TerrainDialog title="Créer" open onClose={onClose} testId="execution-create-menu-dialog">
        <p>Choix</p>
      </TerrainDialog>,
    )

    const dialog = screen.getByRole('dialog')
    expect(dialog.getAttribute('data-testid')).toBe('execution-create-menu-dialog')
    expect(screen.getByRole('heading', { name: 'Créer' })).toBeTruthy()

    fireEvent.keyDown(window, { key: 'Escape' })
    expect(onClose).toHaveBeenCalledTimes(1)

    const scrim = container.querySelector('button.absolute')
    expect(scrim).not.toBeNull()
    fireEvent.click(scrim!)
    expect(onClose).toHaveBeenCalledTimes(2)
  })

  it('ignores scrim and Escape when the dialog is not dismissible', () => {
    const onClose = vi.fn()
    const { container } = render(
      <TerrainDialog title="Créer" open onClose={onClose} dismissible={false} testId="pinned-dialog">
        <p>Choix</p>
      </TerrainDialog>,
    )

    const scrim = container.querySelector('button[disabled]')
    expect(scrim).not.toBeNull()
    fireEvent.click(scrim!)
    fireEvent.keyDown(window, { key: 'Escape' })
    expect(onClose).not.toHaveBeenCalled()
    expect(screen.getByRole('dialog').getAttribute('data-testid')).toBe('pinned-dialog')
  })

  it('yields Escape and Tab while another dialog is stacked above, then resumes', () => {
    const closeLower = vi.fn()
    const closeUpper = vi.fn()
    const { rerender } = render(
      <>
        <button type="button">Avant</button>
        <TerrainDialog title="Bas" open={false} onClose={closeLower}>
          <button type="button">Un</button>
        </TerrainDialog>
      </>,
    )
    const before = screen.getByRole('button', { name: 'Avant' })
    before.focus()

    rerender(
      <>
        <button type="button">Avant</button>
        <TerrainDialog title="Bas" open onClose={closeLower}>
          <button type="button">Un</button>
        </TerrainDialog>
      </>,
    )

    const lower = screen.getByRole('dialog', { name: 'Bas' })
    within(lower).getByRole('button', { name: 'Un' }).focus()
    const lowerButton = within(lower).getByRole('button', { name: 'Un' })
    expect(document.activeElement).toBe(lowerButton)

    rerender(
      <>
        <button type="button">Avant</button>
        <TerrainDialog title="Bas" open onClose={closeLower}>
          <button type="button">Un</button>
        </TerrainDialog>
        <TerrainDialog title="Haut" open onClose={closeUpper}>
          <button type="button">Photo</button>
        </TerrainDialog>
      </>,
    )

    const upper = screen.getByRole('dialog', { name: 'Haut' })
    expect(document.activeElement).toBe(upper)

    fireEvent.keyDown(window, { key: 'Escape' })
    expect(closeUpper).toHaveBeenCalledTimes(1)
    expect(closeLower).not.toHaveBeenCalled()

    fireEvent.keyDown(window, { key: 'Tab' })
    expect(document.activeElement).toBe(within(upper).getByRole('button', { name: 'Fermer' }))

    fireEvent.keyDown(window, { key: 'Tab', shiftKey: true })
    expect(document.activeElement).toBe(within(upper).getByRole('button', { name: 'Photo' }))

    rerender(
      <>
        <button type="button">Avant</button>
        <TerrainDialog title="Bas" open onClose={closeLower}>
          <button type="button">Un</button>
        </TerrainDialog>
      </>,
    )

    expect(document.activeElement).toBe(screen.getByRole('button', { name: 'Un' }))

    fireEvent.keyDown(window, { key: 'Tab' })
    expect(document.activeElement).toBe(within(screen.getByRole('dialog', { name: 'Bas' })).getByRole('button', { name: 'Fermer' }))

    fireEvent.keyDown(window, { key: 'Tab', shiftKey: true })
    expect(document.activeElement).toBe(screen.getByRole('button', { name: 'Un' }))

    fireEvent.keyDown(window, { key: 'Escape' })
    expect(closeLower).toHaveBeenCalledTimes(1)

    rerender(
      <>
        <button type="button">Avant</button>
        <TerrainDialog title="Bas" open={false} onClose={closeLower}>
          <button type="button">Un</button>
        </TerrainDialog>
      </>,
    )
    expect(document.activeElement).toBe(before)
  })
})
