export const DICTATION_TOO_LONG_MESSAGE =
  'La transcription dépasse la taille maximale. Votre brouillon est conservé.'

export type DictationAppendResult =
  | { status: 'appended'; value: string }
  | { status: 'empty' }
  | { status: 'too_long' }

/**
 * Append a full transcription to the current draft.
 * Returns too_long instead of cutting the transcript when it does not fit.
 */
export function appendDictationText(
  existing: string,
  incoming: string,
  maxLength: number,
): DictationAppendResult {
  if (incoming.trim().length === 0) {
    return { status: 'empty' }
  }
  const next =
    existing.trim().length > 0
      ? `${existing}${existing.endsWith(' ') ? '' : ' '}${incoming}`
      : incoming
  if (next.length > maxLength) {
    return { status: 'too_long' }
  }
  return { status: 'appended', value: next }
}
