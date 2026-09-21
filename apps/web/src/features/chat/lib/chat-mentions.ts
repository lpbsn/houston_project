import type { ChatMessageMention } from '../types'

export type ChatMentionDraft = {
  membership_id: string
  start: number
  end: number
}

export function unicodeLength(value: string): number {
  return Array.from(value).length
}

export function unicodeSlice(value: string, start: number, end: number): string {
  return Array.from(value).slice(start, end).join('')
}

export function mentionLabel(displayName: string): string {
  return `@${displayName}`
}

export function trimBodyAndMentions(
  body: string,
  mentions: ChatMentionDraft[],
): { body: string; mentions: ChatMentionDraft[] } {
  const codePoints = Array.from(body)
  let startTrim = 0
  while (startTrim < codePoints.length && /\s/u.test(codePoints[startTrim] ?? '')) {
    startTrim += 1
  }
  let endTrim = codePoints.length
  while (endTrim > startTrim && /\s/u.test(codePoints[endTrim - 1] ?? '')) {
    endTrim -= 1
  }
  const trimmed = codePoints.slice(startTrim, endTrim).join('')
  const shifted = mentions
    .map((mention) => ({
      membership_id: mention.membership_id,
      start: mention.start - startTrim,
      end: mention.end - startTrim,
    }))
    .filter((mention) => mention.start >= 0 && mention.end <= unicodeLength(trimmed))
    .filter((mention) => mention.start < mention.end)
  return { body: trimmed, mentions: shifted }
}

export function reconcileMentions(
  body: string,
  mentions: ChatMentionDraft[],
  expectedLabel: (membershipId: string) => string | null,
): ChatMentionDraft[] {
  return mentions.filter((mention) => {
    if (mention.start < 0 || mention.end > unicodeLength(body) || mention.start >= mention.end) {
      return false
    }
    const label = expectedLabel(mention.membership_id)
    if (!label) {
      return false
    }
    return unicodeSlice(body, mention.start, mention.end) === label
  })
}

export function insertMentionAtCursor(options: {
  body: string
  cursor: number
  displayName: string
  membershipId: string
  existing: ChatMentionDraft[]
}): { body: string; cursor: number; mentions: ChatMentionDraft[] } {
  const codePoints = Array.from(options.body)
  const cursor = Math.max(0, Math.min(options.cursor, codePoints.length))
  let replaceFrom = cursor
  while (replaceFrom > 0 && codePoints[replaceFrom - 1] !== ' ' && codePoints[replaceFrom - 1] !== '\n') {
    replaceFrom -= 1
  }
  if (codePoints[replaceFrom] !== '@') {
    replaceFrom = cursor
  }
  const label = mentionLabel(options.displayName)
  const labelPoints = Array.from(label)
  const nextPoints = [...codePoints.slice(0, replaceFrom), ...labelPoints, ' ', ...codePoints.slice(cursor)]
  const insertedEnd = replaceFrom + labelPoints.length
  const kept = options.existing
    .filter((mention) => mention.end <= replaceFrom || mention.start >= cursor)
    .map((mention) => {
      if (mention.start >= cursor) {
        const delta = labelPoints.length + 1 - (cursor - replaceFrom)
        return {
          ...mention,
          start: mention.start + delta,
          end: mention.end + delta,
        }
      }
      return mention
    })
  return {
    body: nextPoints.join(''),
    cursor: insertedEnd + 1,
    mentions: [
      ...kept,
      { membership_id: options.membershipId, start: replaceFrom, end: insertedEnd },
    ],
  }
}

export function mentionQueryAtCursor(body: string, cursor: number): { start: number; query: string } | null {
  const codePoints = Array.from(body)
  const clamped = Math.max(0, Math.min(cursor, codePoints.length))
  let start = clamped
  while (start > 0 && codePoints[start - 1] !== ' ' && codePoints[start - 1] !== '\n') {
    start -= 1
  }
  if (codePoints[start] !== '@') {
    return null
  }
  const query = codePoints.slice(start + 1, clamped).join('')
  if (query.includes('@')) {
    return null
  }
  return { start, query }
}

export function splitBodyByMentions(
  body: string,
  mentions: Array<Pick<ChatMessageMention, 'start' | 'end' | 'membership_id'>>,
): Array<{ text: string; membershipId?: string }> {
  const sorted = [...mentions].sort((left, right) => left.start - right.start)
  const segments: Array<{ text: string; membershipId?: string }> = []
  let cursor = 0
  const length = unicodeLength(body)
  for (const mention of sorted) {
    if (mention.start < cursor || mention.end > length || mention.start >= mention.end) {
      continue
    }
    if (mention.start > cursor) {
      segments.push({ text: unicodeSlice(body, cursor, mention.start) })
    }
    segments.push({
      text: unicodeSlice(body, mention.start, mention.end),
      membershipId: mention.membership_id,
    })
    cursor = mention.end
  }
  if (cursor < length) {
    segments.push({ text: unicodeSlice(body, cursor, length) })
  }
  return segments
}
