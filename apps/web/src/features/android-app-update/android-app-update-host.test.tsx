// @vitest-environment jsdom

import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { LATER_ACTION_LABEL, SOFT_UPDATE_MESSAGE, UPDATE_ACTION_LABEL } from './constants'

const {
  isAndroidInAppUpdateRuntime,
  readAndroidPlayUpdate,
  startAndroidPlayUpdate,
  completeAndroidFlexibleUpdateIfDownloaded,
  fetchAndroidMinSupportedVersionCode,
  subscribeAppForeground,
} = vi.hoisted(() => ({
  isAndroidInAppUpdateRuntime: vi.fn(() => true),
  readAndroidPlayUpdate: vi.fn(),
  startAndroidPlayUpdate: vi.fn<(preferred: 'immediate' | 'flexible') => Promise<'ok'>>(
    async () => 'ok',
  ),
  completeAndroidFlexibleUpdateIfDownloaded: vi.fn(async () => undefined),
  fetchAndroidMinSupportedVersionCode: vi.fn(async () => 0),
  subscribeAppForeground: vi.fn<(listener: () => void) => () => void>(() => () => undefined),
}))

vi.mock('./play-bridge', () => ({
  isAndroidInAppUpdateRuntime: () => isAndroidInAppUpdateRuntime(),
  readAndroidPlayUpdate: () => readAndroidPlayUpdate(),
  startAndroidPlayUpdate: (preferred: 'immediate' | 'flexible') => startAndroidPlayUpdate(preferred),
  completeAndroidFlexibleUpdateIfDownloaded: () => completeAndroidFlexibleUpdateIfDownloaded(),
}))

vi.mock('./api', () => ({
  fetchAndroidMinSupportedVersionCode: () => fetchAndroidMinSupportedVersionCode(),
}))

vi.mock('@/lib/app-lifecycle', () => ({
  subscribeAppForeground: (listener: () => void) => subscribeAppForeground(listener),
}))

vi.mock('./log', () => ({
  logAndroidAppUpdate: vi.fn(),
}))

import { AndroidAppUpdateHost } from './android-app-update-host'
import { clearAndroidAppUpdateStateForTests, snoozeAndroidAppUpdate } from './storage'

function installablePlay(overrides: Record<string, unknown> = {}) {
  return {
    currentVersionCode: '2',
    availableVersionCode: '3',
    updateAvailability: 2,
    flexibleUpdateAllowed: true,
    immediateUpdateAllowed: true,
    installStatus: null,
    ...overrides,
  }
}

describe('AndroidAppUpdateHost', () => {
  beforeEach(() => {
    isAndroidInAppUpdateRuntime.mockReturnValue(true)
    readAndroidPlayUpdate.mockResolvedValue(installablePlay())
    startAndroidPlayUpdate.mockResolvedValue('ok')
    fetchAndroidMinSupportedVersionCode.mockResolvedValue(0)
    subscribeAppForeground.mockImplementation(() => () => undefined)
  })

  afterEach(() => {
    cleanup()
    clearAndroidAppUpdateStateForTests()
    vi.clearAllMocks()
  })

  it('does not call Play on web or iOS', async () => {
    isAndroidInAppUpdateRuntime.mockReturnValue(false)
    render(
      <AndroidAppUpdateHost>
        <div>app</div>
      </AndroidAppUpdateHost>,
    )
    expect(screen.getByText('app')).toBeTruthy()
    await waitFor(() => {
      expect(readAndroidPlayUpdate).not.toHaveBeenCalled()
    })
    expect(screen.queryByRole('dialog')).toBeNull()
  })

  it('shows the soft popup and snoozes on Later', async () => {
    render(
      <AndroidAppUpdateHost>
        <div>app</div>
      </AndroidAppUpdateHost>,
    )
    await waitFor(() => {
      expect(screen.getByRole('dialog').textContent).toContain(SOFT_UPDATE_MESSAGE)
    })
    screen.getByRole('button', { name: LATER_ACTION_LABEL }).click()
    await waitFor(() => {
      expect(screen.queryByRole('dialog')).toBeNull()
    })
  })

  it('starts the Play flow from Update', async () => {
    render(
      <AndroidAppUpdateHost>
        <div>app</div>
      </AndroidAppUpdateHost>,
    )
    await waitFor(() => {
      expect(screen.getByRole('button', { name: UPDATE_ACTION_LABEL })).toBeTruthy()
    })
    screen.getByRole('button', { name: UPDATE_ACTION_LABEL }).click()
    await waitFor(() => {
      expect(startAndroidPlayUpdate).toHaveBeenCalledWith('flexible')
    })
  })

  it('shows force without Later when below the floor and Play is installable', async () => {
    fetchAndroidMinSupportedVersionCode.mockResolvedValue(9)
    render(
      <AndroidAppUpdateHost>
        <div>app</div>
      </AndroidAppUpdateHost>,
    )
    await waitFor(() => {
      expect(screen.getByRole('button', { name: UPDATE_ACTION_LABEL })).toBeTruthy()
    })
    expect(screen.queryByRole('button', { name: LATER_ACTION_LABEL })).toBeNull()
    screen.getByRole('button', { name: UPDATE_ACTION_LABEL }).click()
    await waitFor(() => {
      expect(startAndroidPlayUpdate).toHaveBeenCalledWith('immediate')
    })
  })

  it('does not show a force overlay when Play has no installable update', async () => {
    fetchAndroidMinSupportedVersionCode.mockResolvedValue(9)
    readAndroidPlayUpdate.mockResolvedValue(
      installablePlay({
        updateAvailability: 1,
        flexibleUpdateAllowed: false,
        immediateUpdateAllowed: false,
      }),
    )
    render(
      <AndroidAppUpdateHost>
        <div>app</div>
      </AndroidAppUpdateHost>,
    )
    await waitFor(() => {
      expect(readAndroidPlayUpdate).toHaveBeenCalled()
    })
    expect(screen.queryByRole('dialog')).toBeNull()
  })

  it('clears a force overlay when a later check has a known non-forcing floor', async () => {
    let onForeground: (() => void) | undefined
    subscribeAppForeground.mockImplementation((listener) => {
      onForeground = listener
      return () => undefined
    })
    fetchAndroidMinSupportedVersionCode.mockResolvedValue(9)
    render(
      <AndroidAppUpdateHost>
        <div>app</div>
      </AndroidAppUpdateHost>,
    )
    await waitFor(() => {
      expect(screen.queryByRole('button', { name: LATER_ACTION_LABEL })).toBeNull()
      expect(screen.getByRole('button', { name: UPDATE_ACTION_LABEL })).toBeTruthy()
    })

    fetchAndroidMinSupportedVersionCode.mockResolvedValue(0)
    clearAndroidAppUpdateStateForTests()
    snoozeAndroidAppUpdate('3', Date.now())
    onForeground?.()
    await waitFor(() => {
      expect(screen.queryByRole('dialog')).toBeNull()
    })
  })

  it('keeps a force overlay if Play info is temporarily missing', async () => {
    let onForeground: (() => void) | undefined
    subscribeAppForeground.mockImplementation((listener) => {
      onForeground = listener
      return () => undefined
    })
    fetchAndroidMinSupportedVersionCode.mockResolvedValue(9)
    render(
      <AndroidAppUpdateHost>
        <div>app</div>
      </AndroidAppUpdateHost>,
    )
    await waitFor(() => {
      expect(screen.queryByRole('button', { name: LATER_ACTION_LABEL })).toBeNull()
      expect(screen.getByRole('button', { name: UPDATE_ACTION_LABEL })).toBeTruthy()
    })

    readAndroidPlayUpdate.mockResolvedValue(null)
    clearAndroidAppUpdateStateForTests()
    onForeground?.()
    await waitFor(() => {
      expect(readAndroidPlayUpdate.mock.calls.length).toBeGreaterThanOrEqual(2)
    })
    expect(screen.queryByRole('button', { name: LATER_ACTION_LABEL })).toBeNull()
    expect(screen.getByRole('button', { name: UPDATE_ACTION_LABEL })).toBeTruthy()
  })

  it('keeps a force overlay if the backend floor is temporarily unknown', async () => {
    let onForeground: (() => void) | undefined
    subscribeAppForeground.mockImplementation((listener) => {
      onForeground = listener
      return () => undefined
    })
    fetchAndroidMinSupportedVersionCode.mockResolvedValue(9)
    render(
      <AndroidAppUpdateHost>
        <div>app</div>
      </AndroidAppUpdateHost>,
    )
    await waitFor(() => {
      expect(screen.queryByRole('button', { name: LATER_ACTION_LABEL })).toBeNull()
      expect(screen.getByRole('button', { name: UPDATE_ACTION_LABEL })).toBeTruthy()
    })

    fetchAndroidMinSupportedVersionCode.mockResolvedValue(null)
    clearAndroidAppUpdateStateForTests()
    onForeground?.()
    await waitFor(() => {
      expect(fetchAndroidMinSupportedVersionCode.mock.calls.length).toBeGreaterThanOrEqual(2)
    })
    expect(screen.queryByRole('button', { name: LATER_ACTION_LABEL })).toBeNull()
    expect(screen.getByRole('button', { name: UPDATE_ACTION_LABEL })).toBeTruthy()
  })

  it('clears a force overlay when Play is known to have nothing installable', async () => {
    let onForeground: (() => void) | undefined
    subscribeAppForeground.mockImplementation((listener) => {
      onForeground = listener
      return () => undefined
    })
    fetchAndroidMinSupportedVersionCode.mockResolvedValue(9)
    render(
      <AndroidAppUpdateHost>
        <div>app</div>
      </AndroidAppUpdateHost>,
    )
    await waitFor(() => {
      expect(screen.getByRole('button', { name: UPDATE_ACTION_LABEL })).toBeTruthy()
    })

    fetchAndroidMinSupportedVersionCode.mockResolvedValue(null)
    readAndroidPlayUpdate.mockResolvedValue(
      installablePlay({
        updateAvailability: 1,
        flexibleUpdateAllowed: false,
        immediateUpdateAllowed: false,
      }),
    )
    clearAndroidAppUpdateStateForTests()
    onForeground?.()
    await waitFor(() => {
      expect(screen.queryByRole('dialog')).toBeNull()
    })
  })

  it('starts Play only once if Update is tapped twice', async () => {
    let resolveUpdate: ((value: 'ok') => void) | undefined
    startAndroidPlayUpdate.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveUpdate = resolve
        }),
    )
    render(
      <AndroidAppUpdateHost>
        <div>app</div>
      </AndroidAppUpdateHost>,
    )
    await waitFor(() => {
      expect(screen.getByRole('button', { name: UPDATE_ACTION_LABEL })).toBeTruthy()
    })
    screen.getByRole('button', { name: UPDATE_ACTION_LABEL }).click()
    screen.getByRole('button', { name: UPDATE_ACTION_LABEL }).click()
    await waitFor(() => {
      expect(startAndroidPlayUpdate).toHaveBeenCalledOnce()
    })
    expect(screen.getByRole('button', { name: UPDATE_ACTION_LABEL })).toHaveProperty('disabled', true)
    resolveUpdate?.('ok')
    await waitFor(() => {
      expect(screen.queryByRole('dialog')).toBeNull()
    })
  })

  it('marks app content inert while a force overlay is open', async () => {
    fetchAndroidMinSupportedVersionCode.mockResolvedValue(9)
    render(
      <AndroidAppUpdateHost>
        <div>app</div>
      </AndroidAppUpdateHost>,
    )
    await waitFor(() => {
      expect(screen.getByRole('button', { name: UPDATE_ACTION_LABEL })).toBeTruthy()
    })
    expect(screen.getByText('app').parentElement?.hasAttribute('inert')).toBe(true)
  })
})
