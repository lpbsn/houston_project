import { describe, expect, it } from 'vitest'

import {
  civilMinutesFromMidnight,
  combineCivilDateTimeToIso,
  splitIsoToCivil,
} from './business-timezone'

describe('business-timezone', () => {
  it('round-trips a civil Paris clock time outside DST gaps', () => {
    const iso = combineCivilDateTimeToIso('2026-09-08', '14:30', 'Europe/Paris')
    expect(splitIsoToCivil(iso, 'Europe/Paris')).toEqual({ date: '2026-09-08', time: '14:30' })
  })

  it('projects midnight UTC vs Paris onto different civil dates', () => {
    const iso = '2026-09-08T22:00:00.000Z'
    expect(splitIsoToCivil(iso, 'UTC')).toEqual({ date: '2026-09-08', time: '22:00' })
    expect(splitIsoToCivil(iso, 'Europe/Paris')).toEqual({ date: '2026-09-09', time: '00:00' })
  })

  it('maps spring-forward Paris instants onto civil minutes, not elapsed duration', () => {
    expect(splitIsoToCivil('2026-03-29T00:30:00.000Z', 'Europe/Paris')).toEqual({
      date: '2026-03-29',
      time: '01:30',
    })
    expect(civilMinutesFromMidnight('2026-03-29T00:30:00.000Z', 'Europe/Paris')).toBe(90)
    expect(splitIsoToCivil('2026-03-29T01:30:00.000Z', 'Europe/Paris')).toEqual({
      date: '2026-03-29',
      time: '03:30',
    })
    expect(civilMinutesFromMidnight('2026-03-29T01:30:00.000Z', 'Europe/Paris')).toBe(210)
  })

  it('collapses both real 02:30 instants on the fall-back day to the same civil minute', () => {
    expect(splitIsoToCivil('2026-10-25T00:30:00.000Z', 'Europe/Paris')).toEqual({
      date: '2026-10-25',
      time: '02:30',
    })
    expect(splitIsoToCivil('2026-10-25T01:30:00.000Z', 'Europe/Paris')).toEqual({
      date: '2026-10-25',
      time: '02:30',
    })
    expect(civilMinutesFromMidnight('2026-10-25T00:30:00.000Z', 'Europe/Paris')).toBe(150)
    expect(civilMinutesFromMidnight('2026-10-25T01:30:00.000Z', 'Europe/Paris')).toBe(150)
  })
})
