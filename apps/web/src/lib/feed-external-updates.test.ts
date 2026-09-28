import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  deferFeedListInvalidation,
  queryKeyMatchesPrefix,
  registerFeedReadingSession,
  removeHydratedFeedEntity,
  resetFeedReadingSessionsForTests,
} from './feed-external-updates'

afterEach(() => {
  resetFeedReadingSessionsForTests()
})

describe('feed external updates', () => {
  it('defers a scrolled feed and still invalidates when the reader is at the top', () => {
    const onDefer = vi.fn()
    const unregister = registerFeedReadingSession({
      matches: (queryKey) => queryKeyMatchesPrefix(queryKey, ['signals', 'feed', 'est-1']),
      atTop: () => false,
      interacting: () => false,
      onDefer,
      onRemove: vi.fn(),
    })

    expect(deferFeedListInvalidation(['signals', 'feed', 'est-1', 'personal'])).toBe(true)
    expect(onDefer).toHaveBeenCalledTimes(1)
    expect(deferFeedListInvalidation(['signals', 'detail', 'est-1'])).toBe(false)

    unregister()
    const atTopDefer = vi.fn()
    registerFeedReadingSession({
      matches: (queryKey) => queryKeyMatchesPrefix(queryKey, ['signals', 'feed', 'est-1']),
      atTop: () => true,
      interacting: () => false,
      onDefer: atTopDefer,
      onRemove: vi.fn(),
    })
    expect(deferFeedListInvalidation(['signals', 'feed', 'est-1'])).toBe(false)
    expect(atTopDefer).not.toHaveBeenCalled()
  })

  it('removes an ineligible entity from the matching session only', () => {
    const onRemove = vi.fn()
    registerFeedReadingSession({
      matches: (queryKey) =>
        queryKeyMatchesPrefix(queryKey, ['action-plans', 'action-plan-execution-feed', 'est-1']),
      atTop: () => false,
      interacting: () => true,
      onDefer: vi.fn(),
      onRemove,
    })

    removeHydratedFeedEntity(
      ['action-plans', 'action-plan-execution-feed', 'est-1'],
      'exec-1',
    )
    removeHydratedFeedEntity(['signals', 'feed', 'est-1'], 'exec-1')

    expect(onRemove).toHaveBeenCalledTimes(1)
    expect(onRemove).toHaveBeenCalledWith('exec-1')
  })
})
