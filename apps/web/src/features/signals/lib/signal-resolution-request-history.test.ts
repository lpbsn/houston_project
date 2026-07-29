import { describe, expect, it } from 'vitest'

import {
  formatResolutionRequestEventLabel,
  formatResolutionRequestHistoryLine,
  type ResolutionRequestHistoryEvent,
} from './signal-resolution-request-history'

function event(
  overrides: Partial<ResolutionRequestHistoryEvent> &
    Pick<ResolutionRequestHistoryEvent, 'event_type'>,
): ResolutionRequestHistoryEvent {
  return {
    request_id: 'req-1',
    occurred_at: '2026-06-30T10:00:00Z',
    actor_display_name: 'Alice',
    ...overrides,
  }
}

describe('formatResolutionRequestEventLabel', () => {
  it('formats created / approved / rejected / canceled with actor', () => {
    expect(formatResolutionRequestEventLabel(event({ event_type: 'created' }))).toBe(
      'Demande de résolution en attente — Envoyée par Alice',
    )
    expect(formatResolutionRequestEventLabel(event({ event_type: 'approved' }))).toBe(
      'Demande de résolution validée — Validée par Alice',
    )
    expect(formatResolutionRequestEventLabel(event({ event_type: 'rejected' }))).toBe(
      'Demande de résolution refusée — Refusée par Alice',
    )
    expect(formatResolutionRequestEventLabel(event({ event_type: 'canceled' }))).toBe(
      'Demande de résolution annulée — Annulée par Alice',
    )
  })

  it('formats auto-cancel without actor', () => {
    expect(
      formatResolutionRequestEventLabel(
        event({ event_type: 'canceled', actor_display_name: null }),
      ),
    ).toBe('Demande de résolution annulée — Annulée automatiquement')
  })
})

describe('formatResolutionRequestHistoryLine', () => {
  it('builds dated lines for create then approve order', () => {
    const lines = [
      event({
        event_type: 'approved',
        occurred_at: '2026-06-30T11:00:00Z',
        actor_display_name: 'Bob',
      }),
      event({
        event_type: 'created',
        occurred_at: '2026-06-30T10:00:00Z',
        actor_display_name: 'Alice',
      }),
    ].map(formatResolutionRequestHistoryLine)

    expect(lines[0]).toContain('Demande de résolution validée — Validée par Bob')
    expect(lines[1]).toContain('Demande de résolution en attente — Envoyée par Alice')
  })

  it('builds dated lines for create then cancel', () => {
    const lines = [
      event({
        event_type: 'canceled',
        occurred_at: '2026-06-30T11:00:00Z',
        actor_display_name: 'Alice',
      }),
      event({ event_type: 'created', occurred_at: '2026-06-30T10:00:00Z' }),
    ].map(formatResolutionRequestHistoryLine)

    expect(lines[0]).toContain('Demande de résolution annulée — Annulée par Alice')
    expect(lines[1]).toContain('Demande de résolution en attente — Envoyée par Alice')
  })

  it('keeps reject then new request as three chronological lines', () => {
    const lines = [
      event({
        request_id: 'req-2',
        event_type: 'created',
        occurred_at: '2026-06-30T12:00:00Z',
        actor_display_name: 'Alice',
      }),
      event({
        request_id: 'req-1',
        event_type: 'rejected',
        occurred_at: '2026-06-30T11:00:00Z',
        actor_display_name: 'Bob',
      }),
      event({
        request_id: 'req-1',
        event_type: 'created',
        occurred_at: '2026-06-30T10:00:00Z',
        actor_display_name: 'Alice',
      }),
    ].map(formatResolutionRequestHistoryLine)

    expect(lines).toHaveLength(3)
    expect(lines[0]).toContain('Envoyée par Alice')
    expect(lines[1]).toContain('Refusée par Bob')
    expect(lines[2]).toContain('Envoyée par Alice')
  })
})
