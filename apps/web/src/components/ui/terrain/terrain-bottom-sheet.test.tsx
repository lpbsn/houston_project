// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { TerrainBottomSheet } from '@/components/ui/terrain/terrain-bottom-sheet'
import {
  dismissTopNativeOverlay,
  resetNativeOverlayDismissForTests,
} from '@/lib/native-overlay-dismiss'
import { terrain } from '@/lib/terrain-styles'

describe('TerrainBottomSheet native overlay dismiss', () => {
  afterEach(() => {
    cleanup()
    resetNativeOverlayDismissForTests()
  })

  it('registers a dismissible sheet on the Android back stack', () => {
    const onClose = vi.fn()
    render(
      <TerrainBottomSheet title="Actions" open onClose={onClose}>
        <p>Contenu</p>
      </TerrainBottomSheet>,
    )

    expect(dismissTopNativeOverlay()).toBe(true)
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('does not close a non-dismissible sheet on Android back', () => {
    const onClose = vi.fn()
    const { container } = render(
      <TerrainBottomSheet title="Actions" open onClose={onClose} dismissible={false}>
        <p>Contenu</p>
      </TerrainBottomSheet>,
    )

    const scrim = container.querySelector('button[disabled]')
    expect(scrim).not.toBeNull()
    fireEvent.click(scrim!)
    expect(onClose).not.toHaveBeenCalled()

    expect(dismissTopNativeOverlay()).toBe(true)
    expect(onClose).not.toHaveBeenCalled()
    expect(dismissTopNativeOverlay()).toBe(true)
    expect(onClose).not.toHaveBeenCalled()
  })
})

describe('TerrainBottomSheet keyboard and safe area', () => {
  afterEach(() => {
    cleanup()
    resetNativeOverlayDismissForTests()
  })

  it('pads the scroll container when there is no footer', () => {
    render(
      <TerrainBottomSheet title="Actions" open onClose={() => undefined}>
        <p>Contenu</p>
      </TerrainBottomSheet>,
    )

    expect(screen.getByText('Contenu').parentElement?.className).toContain(
      'pb-[max(0.75rem,var(--app-safe-bottom))]',
    )
  })

  it('keeps safe-area padding on the footer when one is present', () => {
    render(
      <TerrainBottomSheet title="Actions" open onClose={() => undefined} footer={<button type="button">Valider</button>}>
        <p>Contenu</p>
      </TerrainBottomSheet>,
    )

    expect(screen.getByText('Contenu').parentElement?.className).not.toContain('--app-safe-bottom')
    expect(screen.getByRole('button', { name: 'Valider' }).parentElement?.className).toContain(
      'pb-[max(0.75rem,var(--app-safe-bottom))]',
    )
  })

  it('ignores Escape when the sheet is not dismissible', () => {
    const onClose = vi.fn()
    render(
      <TerrainBottomSheet title="Actions" open onClose={onClose} dismissible={false}>
        <p>Contenu</p>
      </TerrainBottomSheet>,
    )

    fireEvent.keyDown(window, { key: 'Escape' })
    expect(onClose).not.toHaveBeenCalled()
  })

  it('closes on Escape when the sheet is dismissible', () => {
    const onClose = vi.fn()
    render(
      <TerrainBottomSheet title="Actions" open onClose={onClose}>
        <p>Contenu</p>
      </TerrainBottomSheet>,
    )

    fireEvent.keyDown(window, { key: 'Escape' })
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('focuses the dialog on open, traps Tab, and restores focus on close', () => {
    const { rerender } = render(
      <>
        <button type="button">Avant</button>
        <TerrainBottomSheet title="Actions" open={false} onClose={() => undefined}>
          <button type="button">Un</button>
          <button type="button">Deux</button>
        </TerrainBottomSheet>
      </>,
    )
    const before = screen.getByRole('button', { name: 'Avant' })
    before.focus()

    rerender(
      <>
        <button type="button">Avant</button>
        <TerrainBottomSheet title="Actions" open onClose={() => undefined}>
          <button type="button">Un</button>
          <button type="button">Deux</button>
        </TerrainBottomSheet>
      </>,
    )

    const dialog = screen.getByRole('dialog')
    expect(dialog.getAttribute('tabindex')).toBe('-1')
    expect(document.activeElement).toBe(dialog)

    fireEvent.keyDown(window, { key: 'Tab' })
    expect(document.activeElement).toBe(screen.getByRole('button', { name: 'Un' }))

    fireEvent.keyDown(window, { key: 'Tab', shiftKey: true })
    expect(document.activeElement).toBe(screen.getByRole('button', { name: 'Deux' }))

    fireEvent.keyDown(window, { key: 'Tab' })
    expect(document.activeElement).toBe(screen.getByRole('button', { name: 'Un' }))

    rerender(
      <>
        <button type="button">Avant</button>
        <TerrainBottomSheet title="Actions" open={false} onClose={() => undefined}>
          <button type="button">Un</button>
          <button type="button">Deux</button>
        </TerrainBottomSheet>
      </>,
    )
    expect(document.activeElement).toBe(before)
  })

  it('keeps focus on the dialog when nothing inside is focusable', () => {
    render(
      <TerrainBottomSheet title="Actions" open onClose={() => undefined}>
        <p>Contenu</p>
      </TerrainBottomSheet>,
    )

    const dialog = screen.getByRole('dialog')
    expect(document.activeElement).toBe(dialog)
    fireEvent.keyDown(window, { key: 'Tab' })
    expect(document.activeElement).toBe(dialog)
  })
})

describe('TerrainBottomSheet surface color', () => {
  afterEach(() => {
    cleanup()
    resetNativeOverlayDismissForTests()
  })

  it('owns terrain foreground on the white dialog instead of inheriting parent color', () => {
    render(
      <div className="text-white">
        <TerrainBottomSheet title="Actions" open onClose={() => undefined}>
          <input aria-label="Nom" />
        </TerrainBottomSheet>
      </div>,
    )

    expect(screen.getByRole('dialog').className.split(/\s+/)).toEqual(
      expect.arrayContaining(terrain.foreground.split(/\s+/)),
    )
  })
})
