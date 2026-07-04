import { describe, expect, it } from 'vitest'

import { getEmptyFeedDescription } from '@/features/execution/lib/execution-feed-empty'

describe('getEmptyFeedDescription', () => {
  it('describes personal empty feed', () => {
    expect(getEmptyFeedDescription('personal')).toBe(
      'Aucune action, checklist ni plan d’action ne vous est assigné pour le moment.',
    )
  })

  it('describes general empty feed', () => {
    expect(getEmptyFeedDescription('general')).toBe(
      'Aucune action, checklist ni plan d’action visible dans votre périmètre pour le moment.',
    )
  })
})
