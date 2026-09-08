import { describe, expect, it } from 'vitest'

import type { ActionPlanExecutionFeedItem } from '@/features/action-plans/types'

import {
  splitOverlappingColumns,
  timedIntervalOnDay,
} from './execution-calendar-layout'

function item(
  id: string,
  startAt: string,
  endAt: string | null,
  allDay = false,
): ActionPlanExecutionFeedItem {
  return {
    id,
    title: id,
    start_at: startAt,
    end_at: endAt,
    all_day: allDay,
  } as ActionPlanExecutionFeedItem
}

describe('execution-calendar-layout', () => {
  it('places overlapping timed events in adjacent columns', () => {
    const first = {
      item: item('a', '2026-09-08T08:00:00.000Z', '2026-09-08T10:00:00.000Z'),
      startMin: 60,
      endMin: 180,
    }
    const second = {
      item: item('b', '2026-09-08T09:00:00.000Z', '2026-09-08T11:00:00.000Z'),
      startMin: 120,
      endMin: 240,
    }
    const placed = splitOverlappingColumns([first, second])
    expect(placed).toHaveLength(2)
    expect(new Set(placed.map((block) => block.column)).size).toBe(2)
    expect(placed.every((block) => block.columnCount >= 2)).toBe(true)
  })

  it('keeps all-day events out of the timed grid', () => {
    expect(
      timedIntervalOnDay(
        item('all', '2026-09-08T22:00:00.000Z', '2026-09-09T21:59:59.000Z', true),
        '2026-09-08',
      ),
    ).toBeNull()
  })
})
