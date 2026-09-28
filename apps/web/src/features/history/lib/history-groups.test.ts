import { describe, expect, it } from 'vitest'

import { groupHistoryItems, reconcileHistoryItems } from './history-groups'

describe('groupHistoryItems', () => {
  it('keeps one Paris day when items arrive from two pages', () => {
    const groups = groupHistoryItems(
      [
        { id: 'newer', terminal_at: '2026-09-28T16:00:00Z' },
        { id: 'older', terminal_at: '2026-09-28T07:00:00Z' },
      ],
      new Date('2026-09-28T12:00:00Z'),
    )
    expect(groups).toHaveLength(1)
    expect(groups[0]?.items.map((item) => item.id)).toEqual(['newer', 'older'])
    expect(groups[0]?.label).toBe('Aujourd’hui')
  })

  it('keeps the spring-forward civil day together and shows the year when needed', () => {
    const groups = groupHistoryItems(
      [
        { id: 'after', terminal_at: '2026-03-29T20:30:00Z' },
        { id: 'before-jump', terminal_at: '2026-03-28T23:30:00Z' },
        { id: 'previous-year', terminal_at: '2025-03-29T12:00:00Z' },
      ],
      new Date('2026-03-29T10:00:00Z'),
    )
    expect(groups.map((group) => group.key)).toEqual(['2026-03-29', '2025-03-29'])
    expect(groups[0]?.items.map((item) => item.id)).toEqual(['after', 'before-jump'])
    expect(groups[1]?.label.toLowerCase()).toContain('2025')
  })

  it('puts undated items in a single trailing group', () => {
    const groups = groupHistoryItems(
      [
        { id: 'dated', terminal_at: '2026-09-28T12:00:00Z' },
        { id: 'orphan-a', terminal_at: null },
        { id: 'orphan-b', terminal_at: null },
      ],
      new Date('2026-09-28T12:00:00Z'),
    )
    expect(groups.map((group) => group.label)).toEqual(['Aujourd’hui', 'Date inconnue'])
    expect(groups[1]?.items.map((item) => item.id)).toEqual(['orphan-a', 'orphan-b'])
  })

  it('keeps one card per id and uses the latest received representation', () => {
    expect(
      reconcileHistoryItems([
        { id: 'same', terminal_at: '2026-09-28T10:00:00Z', title: 'old' },
        { id: 'other', terminal_at: '2026-09-27T10:00:00Z', title: 'other' },
        { id: 'same', terminal_at: '2026-09-28T11:00:00Z', title: 'new' },
      ]),
    ).toEqual([
      { id: 'same', terminal_at: '2026-09-28T11:00:00Z', title: 'new' },
      { id: 'other', terminal_at: '2026-09-27T10:00:00Z', title: 'other' },
    ])
  })
})
