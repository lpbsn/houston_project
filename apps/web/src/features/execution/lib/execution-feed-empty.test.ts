import { describe, expect, it } from 'vitest'

import { getEmptyFeedDescription } from '@/features/execution/lib/execution-feed-empty'

describe('getEmptyFeedDescription', () => {
  it('describes personal empty feed', () => {
    expect(getEmptyFeedDescription('personal')).toBe(
      'Aucune action ni checklist ne vous est assignée pour le moment.',
    )
  })

  it('describes establishment empty feed', () => {
    expect(getEmptyFeedDescription('establishment')).toBe(
      'Aucune action ni checklist visible dans votre périmètre pour le moment.',
    )
  })
})
