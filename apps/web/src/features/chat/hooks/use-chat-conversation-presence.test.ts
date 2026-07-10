// @vitest-environment jsdom

import { renderHook, act } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { postChatConversationPresence } from '../api'
import { useChatConversationPresence } from './use-chat-conversation-presence'

vi.mock('../api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api')>()
  return {
    ...actual,
    postChatConversationPresence: vi.fn(async () => undefined),
  }
})

const postChatConversationPresenceMock = vi.mocked(postChatConversationPresence)

describe('useChatConversationPresence', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    postChatConversationPresenceMock.mockClear()
    Object.defineProperty(document, 'visibilityState', {
      configurable: true,
      value: 'visible',
    })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('sends presence immediately on mount when visible', () => {
    renderHook(() => useChatConversationPresence('est-1', 'conv-1'))

    expect(postChatConversationPresenceMock).toHaveBeenCalledTimes(1)
    expect(postChatConversationPresenceMock).toHaveBeenCalledWith('est-1', 'conv-1')
  })

  it('sends periodic presence every 30 seconds while visible', () => {
    renderHook(() => useChatConversationPresence('est-1', 'conv-1'))

    act(() => {
      vi.advanceTimersByTime(30_000)
    })

    expect(postChatConversationPresenceMock).toHaveBeenCalledTimes(2)

    act(() => {
      vi.advanceTimersByTime(30_000)
    })

    expect(postChatConversationPresenceMock).toHaveBeenCalledTimes(3)
  })

  it('pauses periodic presence when document is hidden', () => {
    renderHook(() => useChatConversationPresence('est-1', 'conv-1'))

    act(() => {
      Object.defineProperty(document, 'visibilityState', {
        configurable: true,
        value: 'hidden',
      })
      document.dispatchEvent(new Event('visibilitychange'))
    })

    act(() => {
      vi.advanceTimersByTime(60_000)
    })

    expect(postChatConversationPresenceMock).toHaveBeenCalledTimes(1)
  })

  it('sends presence immediately when document becomes visible again', () => {
    renderHook(() => useChatConversationPresence('est-1', 'conv-1'))

    act(() => {
      Object.defineProperty(document, 'visibilityState', {
        configurable: true,
        value: 'hidden',
      })
      document.dispatchEvent(new Event('visibilitychange'))
    })

    const callsAfterHidden = postChatConversationPresenceMock.mock.calls.length

    act(() => {
      Object.defineProperty(document, 'visibilityState', {
        configurable: true,
        value: 'visible',
      })
      document.dispatchEvent(new Event('visibilitychange'))
    })

    expect(postChatConversationPresenceMock.mock.calls.length).toBeGreaterThan(
      callsAfterHidden,
    )
    expect(postChatConversationPresenceMock).toHaveBeenCalledWith('est-1', 'conv-1')
  })

  it('cleans up interval and listener on unmount', () => {
    const removeEventListenerSpy = vi.spyOn(document, 'removeEventListener')
    const { unmount } = renderHook(() => useChatConversationPresence('est-1', 'conv-1'))

    unmount()

    expect(removeEventListenerSpy).toHaveBeenCalledWith(
      'visibilitychange',
      expect.any(Function),
    )

    act(() => {
      vi.advanceTimersByTime(60_000)
    })

    expect(postChatConversationPresenceMock).toHaveBeenCalledTimes(1)
    removeEventListenerSpy.mockRestore()
  })
})
