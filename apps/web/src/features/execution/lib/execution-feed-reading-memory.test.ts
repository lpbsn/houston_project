import { afterEach, describe, expect, it } from 'vitest'

import {
  clearExecutionFeedReadingMemory,
  executionFeedReadingScopeKey,
  readExecutionFeedReading,
  writeExecutionFeedReading,
} from './execution-feed-reading-memory'

describe('execution feed reading memory', () => {
  afterEach(() => {
    clearExecutionFeedReadingMemory()
  })

  it('keeps scroll and open sections for one scope in memory', () => {
    const scopeKey = executionFeedReadingScopeKey('establishment', 'est-1')
    writeExecutionFeedReading(scopeKey, {
      viewMode: 'personal',
      expandedByKey: { done: true },
      scrollTop: 80,
    })

    expect(readExecutionFeedReading(scopeKey)).toEqual({
      viewMode: 'personal',
      expandedByKey: { done: true },
      scrollTop: 80,
    })
    expect(readExecutionFeedReading(executionFeedReadingScopeKey('establishment', 'est-2'))).toBeNull()
    expect(readExecutionFeedReading(executionFeedReadingScopeKey('cross', null))).toBeNull()
  })

  it('clears every scope', () => {
    writeExecutionFeedReading(executionFeedReadingScopeKey('cross', null), {
      viewMode: 'general',
      expandedByKey: {},
      scrollTop: 12,
    })

    clearExecutionFeedReadingMemory()

    expect(readExecutionFeedReading(executionFeedReadingScopeKey('cross', null))).toBeNull()
  })
})
