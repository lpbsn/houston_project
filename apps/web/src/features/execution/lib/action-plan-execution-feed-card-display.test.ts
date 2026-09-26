import { describe, expect, it } from 'vitest'

import {
  formatActionPlanFeedCardDelayLabel,
  formatActionPlanFeedCardStatusLabel,
  formatActionPlanFeedOtherPolesCountLabel,
  formatActionPlanFeedStartCountdownValue,
  formatExecutionFeedCreatedLabel,
  getActionPlanFeedSidebarState,
} from './action-plan-execution-feed-card-display'

const NOW = Date.parse('2026-07-10T12:00:00Z')

describe('formatExecutionFeedCreatedLabel', () => {
  it('formats the created date without a time', () => {
    expect(formatExecutionFeedCreatedLabel('2026-06-30T08:00:00Z')).toMatch(/^Créé le /)
    expect(formatExecutionFeedCreatedLabel('not-a-date')).toBeNull()
  })
})

describe('getActionPlanFeedSidebarState', () => {
  it('returns countdown in hours when end_at is within 24 hours', () => {
    expect(getActionPlanFeedSidebarState('2026-07-10T16:00:00Z', NOW)).toEqual({
      variant: 'countdown',
      prefix: 'DANS',
      value: '4h',
    })
  })

  it('returns countdown in days when end_at is at least 24 hours away', () => {
    expect(getActionPlanFeedSidebarState('2026-07-13T12:00:00Z', NOW)).toEqual({
      variant: 'countdown',
      prefix: 'DANS',
      value: '3j',
    })
  })

  it('returns no_deadline when end_at is absent', () => {
    expect(getActionPlanFeedSidebarState(null, NOW)).toEqual({
      variant: 'no_deadline',
    })
  })

  it('returns no_deadline when end_at is invalid', () => {
    expect(getActionPlanFeedSidebarState('not-a-date', NOW)).toEqual({
      variant: 'no_deadline',
    })
  })

  it.each([
    ['less than one hour', '2026-07-10T11:45:00Z', '1h'],
    ['several hours', '2026-07-10T08:00:00Z', '4h'],
    ['exactly 24 hours', '2026-07-09T12:00:00Z', '1j'],
    ['several days with remaining hours', '2026-07-07T04:00:00Z', '3j'],
  ])('returns overdue duration for %s', (_case, endAt, value) => {
    expect(getActionPlanFeedSidebarState(endAt, NOW, true)).toEqual({
      variant: 'overdue',
      prefix: 'RETARD',
      value,
    })
  })

  it.each([
    ['absent', null],
    ['invalid', 'not-a-date'],
    ['in the future', '2026-07-10T16:00:00Z'],
  ])('returns overdue 0h when end_at is %s', (_case, endAt) => {
    expect(getActionPlanFeedSidebarState(endAt, NOW, true)).toEqual({
      variant: 'overdue',
      prefix: 'RETARD',
      value: '0h',
    })
  })

  it('returns neutral 0h countdown when isOverdue is false and end_at is in the past', () => {
    expect(getActionPlanFeedSidebarState('2026-07-10T11:00:00Z', NOW, false)).toEqual({
      variant: 'countdown',
      prefix: 'DANS',
      value: '0h',
    })
  })

  it('uses a minimum of 1 hour for sub-day remaining time when isOverdue is false', () => {
    expect(getActionPlanFeedSidebarState('2026-07-10T12:15:00Z', NOW)).toEqual({
      variant: 'countdown',
      prefix: 'DANS',
      value: '1h',
    })
  })

  it('returns all_day when allDay is set and not overdue', () => {
    expect(getActionPlanFeedSidebarState('2026-09-08T21:59:00Z', NOW, false, true)).toEqual({
      variant: 'all_day',
    })
  })
})

describe('formatActionPlanFeedCardDelayLabel', () => {
  it('keeps a delay label for an overdue deadline and omits it otherwise', () => {
    expect(formatActionPlanFeedCardDelayLabel('2026-07-10T08:00:00Z', NOW, true)).toMatch(
      /^Retard /,
    )
    expect(formatActionPlanFeedCardDelayLabel('2026-07-10T16:00:00Z', NOW, false)).toBeNull()
  })
})

describe('formatActionPlanFeedStartCountdownValue', () => {
  it.each([
    ['days', 3 * 24 * 60 * 60 * 1000, '3j'],
    ['hours', 7 * 60 * 60 * 1000, '7h'],
    ['under one hour', 30 * 60 * 1000, '<1h'],
    ['zero or past', 0, '<1h'],
    ['negative', -60_000, '<1h'],
  ])('formats %s remaining as %s', (_case, remainingMs, value) => {
    expect(formatActionPlanFeedStartCountdownValue(remainingMs)).toBe(value)
  })
})

describe('formatActionPlanFeedCardStatusLabel', () => {
  it('uses masculine Validé and Planifié feed labels', () => {
    expect(
      formatActionPlanFeedCardStatusLabel({
        status: 'done',
        validated_at: '2026-07-09T10:00:00Z',
      }),
    ).toBe('Validé')
    expect(formatActionPlanFeedCardStatusLabel({ status: 'done', validated_at: null })).toBe(
      'Terminé',
    )
    expect(
      formatActionPlanFeedCardStatusLabel({ status: 'scheduled', validated_at: null }),
    ).toBe('Planifié')
    expect(
      formatActionPlanFeedCardStatusLabel({
        status: 'pending_validation',
        validated_at: null,
      }),
    ).toBe('À valider')
  })
})

describe('formatActionPlanFeedOtherPolesCountLabel', () => {
  it('singularizes one other pole and pluralizes the rest', () => {
    expect(formatActionPlanFeedOtherPolesCountLabel(1)).toBe('+1 pôle')
    expect(formatActionPlanFeedOtherPolesCountLabel(2)).toBe('+2 pôles')
  })
})
