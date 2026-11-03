import { describe, expect, it } from 'vitest'

import { appendDictationText } from './append-dictation-text'

describe('appendDictationText', () => {
  it('uses the transcription when the draft is empty', () => {
    expect(appendDictationText('', 'Bonjour', 100)).toEqual({
      status: 'appended',
      value: 'Bonjour',
    })
    expect(appendDictationText('   ', 'Bonjour', 100)).toEqual({
      status: 'appended',
      value: 'Bonjour',
    })
  })

  it('appends with a single space and keeps the transcript intact', () => {
    expect(appendDictationText('Déjà là', '  suite  ', 100)).toEqual({
      status: 'appended',
      value: 'Déjà là   suite  ',
    })
    expect(appendDictationText('Déjà là ', 'suite', 100)).toEqual({
      status: 'appended',
      value: 'Déjà là suite',
    })
  })

  it('rejects an empty transcription', () => {
    expect(appendDictationText('Brouillon', '   ', 100)).toEqual({ status: 'empty' })
  })

  it('refuses to truncate when the transcription does not fit', () => {
    expect(appendDictationText('abc', 'defghij', 6)).toEqual({ status: 'too_long' })
    expect(appendDictationText('', 'trop long', 4)).toEqual({ status: 'too_long' })
    expect(appendDictationText('abc', 'de', 6)).toEqual({
      status: 'appended',
      value: 'abc de',
    })
  })
})
