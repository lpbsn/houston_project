// @vitest-environment jsdom

import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { AndroidAppUpdateDialog } from './android-app-update-dialog'
import { FORCE_UPDATE_MESSAGE, LATER_ACTION_LABEL, SOFT_UPDATE_MESSAGE, UPDATE_ACTION_LABEL } from './constants'

describe('AndroidAppUpdateDialog', () => {
  afterEach(() => {
    cleanup()
  })

  it('shows the soft copy with Update and Later', () => {
    const onUpdate = vi.fn()
    const onLater = vi.fn()
    render(<AndroidAppUpdateDialog mode="flexible" onUpdate={onUpdate} onLater={onLater} />)
    expect(screen.getByRole('dialog').textContent).toContain(SOFT_UPDATE_MESSAGE)
    screen.getByRole('button', { name: UPDATE_ACTION_LABEL }).click()
    screen.getByRole('button', { name: LATER_ACTION_LABEL }).click()
    expect(onUpdate).toHaveBeenCalledOnce()
    expect(onLater).toHaveBeenCalledOnce()
  })

  it('shows the force copy without Later', () => {
    render(<AndroidAppUpdateDialog mode="force" onUpdate={() => undefined} />)
    expect(screen.getByRole('dialog').textContent).toContain(FORCE_UPDATE_MESSAGE)
    expect(screen.queryByRole('button', { name: LATER_ACTION_LABEL })).toBeNull()
    expect(screen.getByRole('button', { name: UPDATE_ACTION_LABEL })).toBeTruthy()
  })

  it('disables actions while an update is in flight', () => {
    const onUpdate = vi.fn()
    const onLater = vi.fn()
    render(
      <AndroidAppUpdateDialog
        mode="flexible"
        updateBusy
        onUpdate={onUpdate}
        onLater={onLater}
      />,
    )
    expect(screen.getByRole('button', { name: UPDATE_ACTION_LABEL })).toHaveProperty('disabled', true)
    expect(screen.getByRole('button', { name: LATER_ACTION_LABEL })).toHaveProperty('disabled', true)
    screen.getByRole('button', { name: UPDATE_ACTION_LABEL }).click()
    screen.getByRole('button', { name: LATER_ACTION_LABEL }).click()
    expect(onUpdate).not.toHaveBeenCalled()
    expect(onLater).not.toHaveBeenCalled()
  })
})
