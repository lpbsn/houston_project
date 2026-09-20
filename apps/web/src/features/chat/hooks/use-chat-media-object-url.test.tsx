// @vitest-environment jsdom

import { cleanup, render, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

const { fetchAuthenticatedChatMedia } = vi.hoisted(() => ({
  fetchAuthenticatedChatMedia: vi.fn(),
}))

vi.mock('../lib/chat-media', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../lib/chat-media')>()
  return {
    ...actual,
    fetchAuthenticatedChatMedia: (...args: unknown[]) => fetchAuthenticatedChatMedia(...args),
  }
})

import { useChatMediaObjectUrl } from './use-chat-media-object-url'

function Probe({ src }: { src: string }) {
  const { objectUrl, createdByViewer, error } = useChatMediaObjectUrl(src)
  return (
    <div
      data-url={objectUrl ?? ''}
      data-created={createdByViewer ? 'yes' : 'no'}
      data-error={error ? 'yes' : 'no'}
    />
  )
}

describe('useChatMediaObjectUrl', () => {
  afterEach(() => {
    cleanup()
    fetchAuthenticatedChatMedia.mockReset()
    vi.unstubAllGlobals()
  })

  it('revokes a created object URL on unmount', async () => {
    fetchAuthenticatedChatMedia.mockResolvedValue('blob:created-viewer')
    const revokeObjectURL = vi.fn()
    vi.stubGlobal('URL', { ...URL, revokeObjectURL })

    const { unmount, container } = render(<Probe src="/api/v1/chat/preview/" />)
    await waitFor(() => {
      expect(container.firstElementChild?.getAttribute('data-url')).toBe('blob:created-viewer')
    })
    expect(container.firstElementChild?.getAttribute('data-created')).toBe('yes')

    unmount()
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:created-viewer')
  })

  it('does not fetch or revoke an outbox blob src', async () => {
    const revokeObjectURL = vi.fn()
    vi.stubGlobal('URL', { ...URL, revokeObjectURL })

    const { unmount, container } = render(<Probe src="blob:outbox-image" />)
    await waitFor(() => {
      expect(container.firstElementChild?.getAttribute('data-url')).toBe('blob:outbox-image')
    })
    expect(fetchAuthenticatedChatMedia).not.toHaveBeenCalled()
    expect(container.firstElementChild?.getAttribute('data-created')).toBe('no')

    unmount()
    expect(revokeObjectURL).not.toHaveBeenCalled()
  })
})
