import { describe, expect, it } from 'vitest'

import { appendObservationTranscription } from './append-observation-transcription'

describe('appendObservationTranscription', () => {
  it('returns incoming text when existing is empty', () => {
    expect(appendObservationTranscription('', 'Bonjour', 1000)).toBe('Bonjour')
    expect(appendObservationTranscription('   ', 'Bonjour', 1000)).toBe('Bonjour')
  })

  it('appends with a space when existing has content', () => {
    expect(appendObservationTranscription('Déjà là', 'suite', 1000)).toBe('Déjà là suite')
  })

  it('does not double the space when existing already ends with one', () => {
    expect(appendObservationTranscription('Déjà là ', 'suite', 1000)).toBe('Déjà là suite')
  })

  it('caps at maxLength', () => {
    expect(appendObservationTranscription('abc', 'defghij', 6)).toBe('abc de')
  })
})
