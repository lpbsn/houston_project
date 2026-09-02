import { describe, expect, it } from 'vitest'

import { getEmptyFeedDescription } from '@/features/execution/lib/execution-feed-empty'

describe('getEmptyFeedDescription', () => {
  it('describes personal empty feed', () => {
    expect(getEmptyFeedDescription('personal')).toBe(
      'Aucun plan d’action ne vous est assigné pour le moment.',
    )
  })

  it('describes personal empty feed as establishment-wide for owner and director', () => {
    expect(getEmptyFeedDescription('personal', 'owner')).toBe(
      'Aucun plan d’action en cours dans l’établissement.',
    )
    expect(getEmptyFeedDescription('personal', 'director')).toBe(
      'Aucun plan d’action en cours dans l’établissement.',
    )
  })

  it('describes general empty feed', () => {
    expect(getEmptyFeedDescription('general')).toBe(
      'Aucun plan d’action en cours dans l’établissement.',
    )
  })
})
