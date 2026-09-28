import { describe, expect, it } from 'vitest'

import { historyReturnSearch, parseHistorySearch, serializeHistorySearch } from './history-url-state'

describe('history url state', () => {
  it('starts on the last 30 Paris days and all terminal statuses', () => {
    expect(parseHistorySearch('', 'establishment')).toMatchObject({
      kind: 'signals',
      viewMode: 'personal',
      period: '30',
      status: 'all',
    })
    expect(parseHistorySearch('', 'cross').viewMode).toBe('general')
  })

  it('drops a status that does not belong to the selected kind', () => {
    expect(parseHistorySearch('?kind=executions&status=resolved', 'establishment').status).toBe(
      'all',
    )
    expect(parseHistorySearch('?status=done', 'establishment').status).toBe('all')
  })

  it('round-trips a custom period without implying cross', () => {
    const state = parseHistorySearch(
      '?kind=executions&period=custom&from=2026-03-01&to=2026-03-29&view_mode=general',
      'establishment',
    )
    expect(serializeHistorySearch(state, 'establishment')).toBe(
      '?kind=executions&view_mode=general&period=custom&from=2026-03-01&to=2026-03-29',
    )
  })

  it('keeps the custom date when opening a detail', () => {
    const state = parseHistorySearch(
      '?period=custom&from=2026-03-01&to=2026-03-29',
      'establishment',
    )
    const search = historyReturnSearch({ ...state, anchorId: 'sig-1' }, 'establishment')
    expect(search).toContain('from=2026-03-01')
    expect(search).toContain('entry=history')
  })
})
