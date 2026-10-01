// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/react'
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
})
