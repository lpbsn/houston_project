import { describe, expect, it } from 'vitest'

import { getEmptyFeedDescription } from '@/features/execution/lib/execution-feed-empty'

describe('getEmptyFeedDescription', () => {
  it('describes personal empty feed without future wording', () => {
    const description = getEmptyFeedDescription('personal')

    expect(description).toBe('Aucune action ni checklist ne vous est assignée pour le moment.')
    expect(description.toLowerCase()).not.toContain('bientôt')
    expect(description.toLowerCase()).not.toContain('coming soon')
  })

  it('describes establishment empty feed without future wording', () => {
    const description = getEmptyFeedDescription('establishment')

    expect(description).toBe('Aucune action ni checklist visible dans votre périmètre pour le moment.')
    expect(description.toLowerCase()).not.toContain('bientôt')
    expect(description.toLowerCase()).not.toContain('coming soon')
  })
})
