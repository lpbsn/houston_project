/**
 * Append a transcription result onto the current observation compose text.
 * Uses a single space separator when existing content is non-empty after trim.
 */
export function appendObservationTranscription(
  existing: string,
  incoming: string,
  maxLength: number,
): string {
  const next =
    existing.trim().length > 0 ? `${existing}${existing.endsWith(' ') ? '' : ' '}${incoming}` : incoming
  return next.slice(0, maxLength)
}
