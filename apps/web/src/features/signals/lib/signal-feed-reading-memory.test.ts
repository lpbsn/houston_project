import { afterEach, describe, expect, it } from 'vitest'

import {
  clearSignalFeedReadingMemory,
  readSignalFeedReading,
  signalFeedReadingScopeKey,
  writeSignalFeedReading,
} from './signal-feed-reading-memory'

afterEach(() => {
  clearSignalFeedReadingMemory()
})

describe('signal feed reading memory', () => {
  it('keeps view, filters, sections and scroll for one scope', () => {
    const scopeKey = signalFeedReadingScopeKey('establishment', 'est-1')
    writeSignalFeedReading(scopeKey, {
      viewMode: 'general',
      filters: {
        statuses: ['open'],
        businessUnitIds: [],
        activitySubjectIds: [],
        needsQualification: true,
      },
      expandedByKey: { resolved: true },
      scrollTop: 180,
    })

    expect(readSignalFeedReading(scopeKey)).toEqual({
      viewMode: 'general',
      filters: {
        statuses: ['open'],
        businessUnitIds: [],
        activitySubjectIds: [],
        needsQualification: true,
      },
      expandedByKey: { resolved: true },
      scrollTop: 180,
    })
  })

  it('does not apply one scope reading state to another', () => {
    writeSignalFeedReading(signalFeedReadingScopeKey('establishment', 'est-1'), {
      viewMode: 'general',
      scrollTop: 40,
    })
    writeSignalFeedReading(signalFeedReadingScopeKey('cross', null), {
      viewMode: 'personal',
      scrollTop: 12,
    })

    expect(readSignalFeedReading(signalFeedReadingScopeKey('establishment', 'est-2'))).toBeNull()
    expect(readSignalFeedReading(signalFeedReadingScopeKey('cross', null))?.scrollTop).toBe(12)
    expect(readSignalFeedReading(signalFeedReadingScopeKey('establishment', 'est-1'))?.viewMode).toBe(
      'general',
    )
  })
})
