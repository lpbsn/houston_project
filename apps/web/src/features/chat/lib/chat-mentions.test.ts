import { describe, expect, it } from 'vitest'

import {
  insertMentionAtCursor,
  mentionQueryAtCursor,
  splitBodyByMentions,
  trimBodyAndMentions,
  unicodeLength,
} from './chat-mentions'

describe('chat-mentions', () => {
  it('trims body and shifts Unicode offsets', () => {
    const body = '  @Léa hello  '
    const mention = { membership_id: 'm-1', start: 2, end: 6 }
    const result = trimBodyAndMentions(body, [mention])

    expect(result.body).toBe('@Léa hello')
    expect(result.mentions).toEqual([{ membership_id: 'm-1', start: 0, end: 4 }])
    expect(unicodeLength(result.body.slice())).toBe(10)
  })

  it('renders mention spans from offsets without parsing the name', () => {
    const body = 'Hi @Renamed later'
    const segments = splitBodyByMentions(body, [
      { membership_id: 'm-1', start: 3, end: 11 },
    ])

    expect(segments).toEqual([
      { text: 'Hi ' },
      { text: '@Renamed', membershipId: 'm-1' },
      { text: ' later' },
    ])
  })

  it('inserts the picker label and exposes an @ query for a11y picker', () => {
    const inserted = insertMentionAtCursor({
      body: 'Hey @al',
      cursor: 7,
      displayName: 'Alice',
      membershipId: 'm-alice',
      existing: [],
    })

    expect(inserted.body).toBe('Hey @Alice ')
    expect(inserted.mentions).toEqual([{ membership_id: 'm-alice', start: 4, end: 10 }])
    expect(mentionQueryAtCursor('Hey @al', 7)).toEqual({ start: 4, query: 'al' })
  })
})
