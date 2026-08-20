// @vitest-environment jsdom

import { cleanup, fireEvent, render } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { TerrainBottomSheet } from '@/components/ui/terrain/terrain-bottom-sheet'
import {
  dismissTopNativeOverlay,
  resetNativeOverlayDismissForTests,
} from '@/lib/native-overlay-dismiss'

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

  it('closes a non-dismissible sheet on Android back without enabling the scrim', () => {
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
    expect(onClose).toHaveBeenCalledTimes(1)
  })
})
