import { describe, expect, it } from 'vitest'
import { liveSourceHref, readFrozenSource } from './display'

describe('terrain evidence citations', () => {
  it('preserves the frozen evidence identity while opening its parent plan', () => {
    const source = readFrozenSource({ item_id: 'frozen', category: 'terrain_evidence',
      title: 'Évaluation de la réalisation', locators: [
        { format: 'spore_execution', source_id: 'plan-1' }, { source_id: 'review-1' },
      ] })!
    expect(source.itemId).toBe('frozen')
    expect(source.category).toBe('terrain_evidence')
    expect(liveSourceHref('site', source.liveCategory!, source.sourceId)).toBe('/e/site/execution/plan-1')
  })
  it('links an individual aggregated fact to its signal, not to a candidate id', () => {
    const source = readFrozenSource({ category: 'terrain_evidence',
      locators: [{ format: 'spore_signal', source_id: 'signal-1' }, { source_id: 'candidate-1' }] })!
    expect(liveSourceHref('site', source.liveCategory!, source.sourceId)).toBe('/e/site/signals/signal-1')
  })
  it('does not invent navigation for old evidence without a parent locator', () => {
    const source = readFrozenSource({ category: 'terrain_evidence', locators: [{ source_id: 'candidate-1' }] })!
    expect(liveSourceHref('site', source.liveCategory ?? source.category, source.sourceId)).toBeNull()
  })
})
