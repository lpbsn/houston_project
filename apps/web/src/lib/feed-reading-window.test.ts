import { describe, expect, it } from 'vitest'

import {
  FEED_FOCUS_PAGE_LIMIT,
  appendForwardPage,
  continuationPageStalled,
  emptyFeedReadingWindow,
  prependBehindPage,
  removeHydratedItem,
  renderedItems,
  replaceWithFirstPage,
  showRetainedPageOne,
  windowHead,
} from './feed-reading-window'

type Row = { id: string; title: string }

function slot(items: Row[], nextCursor: string | null, hasMore: boolean) {
  return {
    requestCursor: null,
    nextCursor,
    hasMore,
    items,
  }
}

describe('feed reading window', () => {
  it('keeps page one and evicts the back of the focus once the window is full', () => {
    let window = replaceWithFirstPage(
      emptyFeedReadingWindow<Row>(),
      slot([{ id: 'p1', title: 'one' }], 'c1', true),
      1,
    )

    for (let index = 0; index < FEED_FOCUS_PAGE_LIMIT + 1; index += 1) {
      const requested = windowHead(window)!.nextCursor!
      const appended = appendForwardPage(
        window,
        requested,
        {
          items: [{ id: `p${index + 2}`, title: `page-${index + 2}` }],
          nextCursor: `c${index + 2}`,
          hasMore: true,
        },
        (item) => item.id,
      )
      expect(appended.stalled).toBe(false)
      expect(appended.ignored).toBe(false)
      window = appended.window
    }

    expect(window.pageOne?.items.map((item) => item.id)).toEqual(['p1'])
    expect(window.focus).toHaveLength(FEED_FOCUS_PAGE_LIMIT)
    expect(window.focus[0]?.requestCursor).toBe('c2')
    expect(window.behindCursor).toBe('c1')
    expect(renderedItems(window, (item) => item.id).map((item) => item.id)).toEqual([
      'p3',
      'p4',
    ])
    expect(renderedItems(window, (item) => item.id).some((item) => item.id === 'p1')).toBe(false)
  })

  it('restores one page behind the window and does not keep a cursor chain', () => {
    let window = replaceWithFirstPage(
      emptyFeedReadingWindow<Row>(),
      slot([{ id: 'p1', title: 'one' }], 'c1', true),
      1,
    )
    window = appendForwardPage(
      window,
      'c1',
      { items: [{ id: 'p2', title: 'two' }], nextCursor: 'c2', hasMore: true },
      (item) => item.id,
    ).window
    window = appendForwardPage(
      window,
      'c2',
      { items: [{ id: 'p3', title: 'three' }], nextCursor: 'c3', hasMore: true },
      (item) => item.id,
    ).window
    window = appendForwardPage(
      window,
      'c3',
      { items: [{ id: 'p4', title: 'four' }], nextCursor: null, hasMore: false },
      (item) => item.id,
    ).window

    const restored = prependBehindPage(
      window,
      { items: [{ id: 'p2', title: 'two' }], nextCursor: 'c2', hasMore: true },
      (item) => item.id,
    )
    expect(restored.ignored).toBe(false)
    expect(restored.window.behindCursor).toBeNull()
    expect(restored.window.focus.map((entry) => entry.requestCursor)).toEqual(['c1', 'c2'])
    expect(renderedItems(restored.window, (item) => item.id).map((item) => item.id)).toEqual([
      'p1',
      'p2',
      'p3',
    ])
  })

  it('does not splice a behind page that no longer chains to the window', () => {
    let window = replaceWithFirstPage(
      emptyFeedReadingWindow<Row>(),
      slot([{ id: 'p1', title: 'one' }], 'c1', true),
      1,
    )
    window = appendForwardPage(
      window,
      'c1',
      { items: [{ id: 'p2', title: 'two' }], nextCursor: 'c2', hasMore: true },
      (item) => item.id,
    ).window
    window = appendForwardPage(
      window,
      'c2',
      { items: [{ id: 'p3', title: 'three' }], nextCursor: 'c3', hasMore: true },
      (item) => item.id,
    ).window
    window = appendForwardPage(
      window,
      'c3',
      { items: [{ id: 'p4', title: 'four' }], nextCursor: null, hasMore: false },
      (item) => item.id,
    ).window

    const restored = prependBehindPage(
      window,
      { items: [{ id: 'other', title: 'other' }], nextCursor: 'elsewhere', hasMore: true },
      (item) => item.id,
    )
    expect(restored.stalled).toBe(true)
    expect(renderedItems(restored.window, (item) => item.id).map((item) => item.id)).toEqual([
      'p3',
      'p4',
    ])
  })

  it('stops a continuation that does not advance and ignores a stale cursor', () => {
    const window = replaceWithFirstPage(
      emptyFeedReadingWindow<Row>(),
      slot([{ id: 'p1', title: 'one' }], 'c1', true),
      4,
    )
    expect(continuationPageStalled('c1', { items: [], nextCursor: 'c1', hasMore: true })).toBe(
      true,
    )
    const stalled = appendForwardPage(
      window,
      'c1',
      { items: [], nextCursor: 'c1', hasMore: true },
      (item) => item.id,
    )
    expect(stalled.stalled).toBe(true)
    expect(stalled.window.pageOne?.items).toHaveLength(1)
    expect(stalled.window.focus).toEqual([])

    const ignored = appendForwardPage(
      window,
      'older-cursor',
      { items: [{ id: 'x', title: 'x' }], nextCursor: null, hasMore: false },
      (item) => item.id,
    )
    expect(ignored.ignored).toBe(true)
    expect(ignored.window.generation).toBe(4)
  })

  it('dedupes hydrated ids and lets a later copy replace the payload in place', () => {
    let window = replaceWithFirstPage(
      emptyFeedReadingWindow<Row>(),
      slot([{ id: 'same', title: 'old' }], 'c1', true),
      1,
    )
    window = appendForwardPage(
      window,
      'c1',
      { items: [{ id: 'same', title: 'new' }, { id: 'other', title: 'other' }], nextCursor: null, hasMore: false },
      (item) => item.id,
    ).window
    expect(renderedItems(window, (item) => item.id)).toEqual([
      { id: 'same', title: 'new' },
      { id: 'other', title: 'other' },
    ])
  })

  it('drops an ineligible id and keeps a neighbor', () => {
    const window = replaceWithFirstPage(
      emptyFeedReadingWindow<Row>(),
      slot(
        [
          { id: 'a', title: 'a' },
          { id: 'b', title: 'b' },
          { id: 'c', title: 'c' },
        ],
        null,
        false,
      ),
      1,
    )
    const removed = removeHydratedItem(window, 'b', (item) => item.id)
    expect(removed.removed).toBe(true)
    expect(removed.neighborId).toBe('c')
    expect(renderedItems(removed.window, (item) => item.id).map((item) => item.id)).toEqual([
      'a',
      'c',
    ])
  })

  it('returns to the retained first page without restoring evicted cursors', () => {
    let window = replaceWithFirstPage(
      emptyFeedReadingWindow<Row>(),
      slot([{ id: 'p1', title: 'one' }], 'c1', true),
      2,
    )
    window = appendForwardPage(
      window,
      'c1',
      { items: [{ id: 'p2', title: 'two' }], nextCursor: 'c2', hasMore: true },
      (item) => item.id,
    ).window
    window = appendForwardPage(
      window,
      'c2',
      { items: [{ id: 'p3', title: 'three' }], nextCursor: 'c3', hasMore: true },
      (item) => item.id,
    ).window
    window = appendForwardPage(
      window,
      'c3',
      { items: [{ id: 'p4', title: 'four' }], nextCursor: null, hasMore: false },
      (item) => item.id,
    ).window
    const top = showRetainedPageOne(window)
    expect(top.generation).toBe(2)
    expect(top.focus).toEqual([])
    expect(top.behindCursor).toBeNull()
    expect(renderedItems(top, (item) => item.id).map((item) => item.id)).toEqual(['p1'])
  })
})
