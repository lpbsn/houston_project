import { describe, expect, it } from 'vitest'

import {
  appendExecutionFeedSearch,
  parseExecutionFeedSearch,
  serializeExecutionFeedSearch,
} from './execution-feed-url-state'

describe('execution-feed-url-state', () => {
  it('serializes calendar layout params and omits list defaults', () => {
    expect(
      serializeExecutionFeedSearch({
        layout: 'list',
        granularity: 'week',
        anchor: '2026-09-08',
        viewMode: 'personal',
      }),
    ).toBe('')
    expect(
      serializeExecutionFeedSearch({
        layout: 'calendar',
        granularity: 'day',
        anchor: '2026-09-08',
        viewMode: 'general',
      }),
    ).toBe('?layout=calendar&granularity=day&anchor=2026-09-08&view_mode=general')
  })

  it('parses calendar search and keeps defaults for unknown values', () => {
    const parsed = parseExecutionFeedSearch(
      '?layout=calendar&granularity=week&anchor=2026-09-08&view_mode=general',
      new Date('2026-09-08T10:00:00.000Z'),
    )
    expect(parsed).toEqual({
      layout: 'calendar',
      granularity: 'week',
      anchor: '2026-09-08',
      viewMode: 'general',
    })
  })

  it('copies feed params onto a detail path without dropping comment or focus keys', () => {
    expect(
      appendExecutionFeedSearch(
        '/action-plans/executions/exec-1',
        '?layout=calendar&granularity=week&anchor=2026-09-08&tab=comments&commentId=c-1&focus=validation',
      ),
    ).toBe(
      '/action-plans/executions/exec-1?layout=calendar&granularity=week&anchor=2026-09-08&tab=comments&commentId=c-1&focus=validation',
    )
  })

  it('defaults missing view_mode to general only when asked', () => {
    expect(
      parseExecutionFeedSearch('', new Date('2026-09-08T10:00:00.000Z')).viewMode,
    ).toBe('personal')
    expect(
      parseExecutionFeedSearch('', new Date('2026-09-08T10:00:00.000Z'), {
        defaultViewMode: 'general',
      }).viewMode,
    ).toBe('general')
    expect(
      serializeExecutionFeedSearch(
        {
          layout: 'list',
          granularity: 'week',
          anchor: '2026-09-08',
          viewMode: 'general',
        },
        { defaultViewMode: 'general' },
      ),
    ).toBe('')
    expect(
      serializeExecutionFeedSearch(
        {
          layout: 'list',
          granularity: 'week',
          anchor: '2026-09-08',
          viewMode: 'personal',
        },
        { defaultViewMode: 'general' },
      ),
    ).toBe('?view_mode=personal')
  })
})
