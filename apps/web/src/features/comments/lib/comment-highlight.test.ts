// @vitest-environment jsdom

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { CommentItem, ExecutionCommentListItem } from '../types'
import {
  commentDomId,
  commentExistsInExecutionList,
  commentExistsInSignalList,
  SCROLL_RETRY_MAX_ATTEMPTS,
  scrollCommentIntoList,
  scrollToHighlightedComment,
} from './comment-highlight'

describe('comment highlight helpers', () => {
  it('builds stable dom ids', () => {
    expect(commentDomId('comment-1')).toBe('comment-comment-1')
  })

  it('detects signal comments in a flat list', () => {
    const comments: CommentItem[] = [
      {
        id: 'comment-1',
        origin: 'signal',
        body: 'hello',
        author: { membership_id: 'm-1', display_name: 'Alice' },
        mentions: [],
        created_at: '2026-06-15T10:00:00Z',
      },
    ]

    expect(commentExistsInSignalList(comments, 'comment-1')).toBe(true)
    expect(commentExistsInSignalList(comments, 'missing')).toBe(false)
  })

  it('detects execution root and reply comments', () => {
    const comments: ExecutionCommentListItem[] = [
      {
        item_type: 'execution_thread',
        id: 'root-1',
        origin: 'action_plan_execution',
        body: 'root',
        author: { membership_id: 'm-1', display_name: 'Alice' },
        mentions: [],
        created_at: '2026-06-15T10:00:00Z',
        replies: [
          {
            id: 'reply-1',
            origin: 'action_plan_execution',
            body: 'reply',
            author: { membership_id: 'm-2', display_name: 'Bob' },
            mentions: [],
            created_at: '2026-06-15T11:00:00Z',
          },
        ],
        is_resolved: true,
        resolved_at: '2026-06-15T12:00:00Z',
        resolved_by: { membership_id: 'm-1', display_name: 'Alice' },
        permission_hints: { can_reply: true, can_resolve: false },
      },
    ]

    expect(commentExistsInExecutionList(comments, 'root-1')).toBe(true)
    expect(commentExistsInExecutionList(comments, 'reply-1')).toBe(true)
    expect(commentExistsInExecutionList(comments, 'missing')).toBe(false)
  })
})

describe('scrollToHighlightedComment', () => {
  const scrollIntoView = vi.fn()

  function mockMatchMedia(matches: boolean) {
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      configurable: true,
      value: vi.fn().mockImplementation(() => ({
        matches,
        media: '',
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    })
  }

  beforeEach(() => {
    mockMatchMedia(false)
    vi.spyOn(window, 'requestAnimationFrame').mockImplementation((callback) => {
      callback(0)
      return 1
    })
    vi.spyOn(window, 'cancelAnimationFrame').mockImplementation(() => {})
    scrollIntoView.mockReset()
  })

  afterEach(() => {
    vi.restoreAllMocks()
    document.body.innerHTML = ''
  })

  it('scrolls to the comment element when present', () => {
    const element = document.createElement('div')
    element.id = commentDomId('target-1')
    element.scrollIntoView = scrollIntoView
    document.body.appendChild(element)

    scrollToHighlightedComment('target-1')

    expect(scrollIntoView).toHaveBeenCalledWith({
      block: 'center',
      behavior: 'smooth',
    })
  })

  it('retries until the comment element appears', () => {
    let frame = 0
    vi.spyOn(window, 'requestAnimationFrame').mockImplementation((callback) => {
      frame += 1
      if (frame === 2) {
        const element = document.createElement('div')
        element.id = commentDomId('delayed-target')
        element.scrollIntoView = scrollIntoView
        document.body.appendChild(element)
      }
      callback(0)
      return frame
    })

    scrollToHighlightedComment('delayed-target')

    expect(scrollIntoView).toHaveBeenCalledTimes(1)
    expect(frame).toBe(2)
  })

  it('stops retrying after max attempts', () => {
    let frame = 0
    vi.spyOn(window, 'requestAnimationFrame').mockImplementation((callback) => {
      frame += 1
      callback(0)
      return frame
    })

    scrollToHighlightedComment('missing-target')

    expect(scrollIntoView).not.toHaveBeenCalled()
    expect(frame).toBe(SCROLL_RETRY_MAX_ATTEMPTS)
  })

  it('uses auto scroll behavior when reduced motion is preferred', () => {
    mockMatchMedia(true)

    const element = document.createElement('div')
    element.id = commentDomId('motion-target')
    element.scrollIntoView = scrollIntoView
    document.body.appendChild(element)

    scrollToHighlightedComment('motion-target')

    expect(scrollIntoView).toHaveBeenCalledWith({
      block: 'center',
      behavior: 'auto',
    })
  })

  it('cancels pending retries when cleanup is called', () => {
    let frame = 0
    let pendingCallback: FrameRequestCallback | null = null
    vi.spyOn(window, 'requestAnimationFrame').mockImplementation((callback) => {
      frame += 1
      if (frame === 1) {
        pendingCallback = callback
        return frame
      }
      callback(0)
      return frame
    })

    const cancel = scrollToHighlightedComment('missing-target')
    expect(frame).toBe(1)

    cancel()
    pendingCallback?.(0)

    expect(frame).toBe(1)
    expect(scrollIntoView).not.toHaveBeenCalled()
  })
})

describe('scrollCommentIntoList', () => {
  const scrollIntoView = vi.fn()
  const scrollTo = vi.fn()

  function mockMatchMedia(matches: boolean) {
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      configurable: true,
      value: vi.fn().mockImplementation(() => ({
        matches,
        media: '',
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    })
  }

  function mountCommentInList() {
    const list = document.createElement('ul')
    list.style.overflowY = 'auto'
    Object.defineProperty(list, 'clientHeight', { configurable: true, value: 100 })
    Object.defineProperty(list, 'scrollHeight', { configurable: true, value: 400 })
    list.scrollTop = 10
    list.scrollTo = scrollTo
    vi.spyOn(list, 'getBoundingClientRect').mockReturnValue({
      top: 0,
      height: 100,
      left: 0,
      right: 0,
      bottom: 100,
      width: 0,
      x: 0,
      y: 0,
      toJSON: () => ({}),
    })

    const element = document.createElement('li')
    element.id = commentDomId('list-target')
    element.scrollIntoView = scrollIntoView
    vi.spyOn(element, 'getBoundingClientRect').mockReturnValue({
      top: 200,
      height: 40,
      left: 0,
      right: 0,
      bottom: 240,
      width: 0,
      x: 0,
      y: 200,
      toJSON: () => ({}),
    })

    list.appendChild(element)
    document.body.appendChild(list)
    return { list, element }
  }

  beforeEach(() => {
    mockMatchMedia(false)
    vi.spyOn(window, 'requestAnimationFrame').mockImplementation((callback) => {
      callback(0)
      return 1
    })
    vi.spyOn(window, 'cancelAnimationFrame').mockImplementation(() => {})
    scrollIntoView.mockReset()
    scrollTo.mockReset()
  })

  afterEach(() => {
    vi.restoreAllMocks()
    document.body.innerHTML = ''
  })

  it('scrolls the nearest list scroller without calling scrollIntoView', () => {
    mountCommentInList()

    scrollCommentIntoList('list-target')

    expect(scrollTo).toHaveBeenCalledWith({
      top: 180,
      behavior: 'smooth',
    })
    expect(scrollIntoView).not.toHaveBeenCalled()
  })

  it('skips a non-overflowing list and scrolls the next real scroller', () => {
    const listScrollTo = vi.fn()
    const main = document.createElement('main')
    main.style.overflowY = 'auto'
    Object.defineProperty(main, 'clientHeight', { configurable: true, value: 100 })
    Object.defineProperty(main, 'scrollHeight', { configurable: true, value: 400 })
    main.scrollTop = 0
    main.scrollTo = scrollTo
    vi.spyOn(main, 'getBoundingClientRect').mockReturnValue({
      top: 0,
      height: 100,
      left: 0,
      right: 0,
      bottom: 100,
      width: 0,
      x: 0,
      y: 0,
      toJSON: () => ({}),
    })

    const list = document.createElement('ul')
    list.style.overflowY = 'auto'
    Object.defineProperty(list, 'clientHeight', { configurable: true, value: 300 })
    Object.defineProperty(list, 'scrollHeight', { configurable: true, value: 300 })
    list.scrollTo = listScrollTo

    const element = document.createElement('li')
    element.id = commentDomId('page-target')
    element.scrollIntoView = scrollIntoView
    vi.spyOn(element, 'getBoundingClientRect').mockReturnValue({
      top: 200,
      height: 40,
      left: 0,
      right: 0,
      bottom: 240,
      width: 0,
      x: 0,
      y: 200,
      toJSON: () => ({}),
    })

    list.appendChild(element)
    main.appendChild(list)
    document.body.appendChild(main)

    scrollCommentIntoList('page-target')

    expect(listScrollTo).not.toHaveBeenCalled()
    expect(scrollTo).toHaveBeenCalledWith({
      top: 170,
      behavior: 'smooth',
    })
    expect(scrollIntoView).not.toHaveBeenCalled()
  })

  it('clamps scrollTop to the scroller range', () => {
    const list = document.createElement('ul')
    list.style.overflowY = 'auto'
    Object.defineProperty(list, 'clientHeight', { configurable: true, value: 100 })
    Object.defineProperty(list, 'scrollHeight', { configurable: true, value: 140 })
    list.scrollTop = 0
    list.scrollTo = scrollTo
    vi.spyOn(list, 'getBoundingClientRect').mockReturnValue({
      top: 0,
      height: 100,
      left: 0,
      right: 0,
      bottom: 100,
      width: 0,
      x: 0,
      y: 0,
      toJSON: () => ({}),
    })

    const element = document.createElement('li')
    element.id = commentDomId('clamp-target')
    element.scrollIntoView = scrollIntoView
    vi.spyOn(element, 'getBoundingClientRect').mockReturnValue({
      top: 200,
      height: 40,
      left: 0,
      right: 0,
      bottom: 240,
      width: 0,
      x: 0,
      y: 200,
      toJSON: () => ({}),
    })

    list.appendChild(element)
    document.body.appendChild(list)

    scrollCommentIntoList('clamp-target')

    expect(scrollTo).toHaveBeenCalledWith({
      top: 40,
      behavior: 'smooth',
    })
    expect(scrollIntoView).not.toHaveBeenCalled()
  })

  it('does nothing when there is no internal overflow scroller', () => {
    const element = document.createElement('div')
    element.id = commentDomId('uncontained-target')
    element.scrollIntoView = scrollIntoView
    document.body.appendChild(element)

    scrollCommentIntoList('uncontained-target')

    expect(scrollTo).not.toHaveBeenCalled()
    expect(scrollIntoView).not.toHaveBeenCalled()
  })

  it('stops retrying after max attempts', () => {
    let frame = 0
    vi.spyOn(window, 'requestAnimationFrame').mockImplementation((callback) => {
      frame += 1
      callback(0)
      return frame
    })

    scrollCommentIntoList('missing-target')

    expect(scrollTo).not.toHaveBeenCalled()
    expect(scrollIntoView).not.toHaveBeenCalled()
    expect(frame).toBe(SCROLL_RETRY_MAX_ATTEMPTS)
  })

  it('uses auto scroll behavior when reduced motion is preferred', () => {
    mockMatchMedia(true)
    mountCommentInList()

    scrollCommentIntoList('list-target')

    expect(scrollTo).toHaveBeenCalledWith({
      top: 180,
      behavior: 'auto',
    })
    expect(scrollIntoView).not.toHaveBeenCalled()
  })

  it('cancels pending retries when cleanup is called', () => {
    let frame = 0
    let pendingCallback: FrameRequestCallback | null = null
    vi.spyOn(window, 'requestAnimationFrame').mockImplementation((callback) => {
      frame += 1
      if (frame === 1) {
        pendingCallback = callback
        return frame
      }
      callback(0)
      return frame
    })

    const cancel = scrollCommentIntoList('missing-target')
    expect(frame).toBe(1)

    cancel()
    pendingCallback?.(0)

    expect(frame).toBe(1)
    expect(scrollTo).not.toHaveBeenCalled()
    expect(scrollIntoView).not.toHaveBeenCalled()
  })
})
