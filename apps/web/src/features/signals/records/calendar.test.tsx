// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { monthWindow, recordWeekSpans, RecordCalendar } from './calendar'
import type { FieldRecord } from './api'

afterEach(cleanup)
function record(
  id: string,
  start: string,
  end: string,
  due = end,
): FieldRecord {
  return {
    id,
    title: `Sujet ${id}`,
    summary: '',
    kind: 'observation',
    stage: 'doing',
    closure_reason: '',
    is_pinned: false,
    pole: 'Restaurant',
    pole_id: null,
    color_index: null,
    owner: null,
    waiting_for: null,
    due_on: due,
    blocked_reason: '',
    created_at: `${start}T12:00:00Z`,
    updated_at: `${end}T12:00:00Z`,
    observation_count: 2,
    calendar: { start, end, due, overdue: due < end },
    can_manage: true,
    can_progress: true,
    can_use_brain: true,
  }
}
describe('calendrier des fiches', () => {
  it('couvre six semaines complètes commençant un lundi', () => {
    const window = monthWindow('2026-11')
    expect(window.days).toHaveLength(42)
    expect(window.from).toBe('2026-10-26')
    expect(window.to).toBe('2026-12-06')
  })
  it('garde une bande continue et sépare les sujets qui se chevauchent', () => {
    const a = record('a', '2026-10-29', '2026-11-05')
    const b = record('b', '2026-11-03', '2026-11-07')
    const spans = recordWeekSpans([b, a], '2026-11-02', '2026-11-08')
    expect(spans.map((s) => [s.record.id, s.start, s.end, s.lane])).toEqual([
      ['a', 0, 3, 0],
      ['b', 1, 5, 1],
    ])
  })
  it('n’étend pas une résolution au-delà de sa fin et ignore les fiches non datées', () => {
    const closed = {
      ...record('a', '2026-10-29', '2026-11-03', '2026-11-07'),
      stage: 'closed' as const,
    }
    const undated = {
      ...record('b', '2026-11-01', '2026-11-07'),
      calendar: null,
      due_on: null,
    }
    const spans = recordWeekSpans([closed, undated], '2026-11-02', '2026-11-08')
    expect(spans).toHaveLength(1)
    expect(spans[0].end).toBe(1)
  })
  it('ouvre la même fiche depuis chaque segment hebdomadaire et conserve l’échéance', () => {
    const open = vi.fn()
    render(
      <RecordCalendar
        month="2026-11"
        records={[record('a', '2026-10-29', '2026-11-05', '2026-11-03')]}
        onOpen={open}
      />,
    )
    const segments = screen.getAllByRole('button', { name: /Sujet a/ })
    expect(segments).toHaveLength(2)
    fireEvent.click(segments[1])
    expect(open).toHaveBeenCalledWith('a')
    expect(segments[1].textContent).toContain('◆ 3')
  })
})
