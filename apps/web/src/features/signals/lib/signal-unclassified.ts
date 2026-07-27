/**
 * Badge and feed filter « Non classifié » share this predicate:
 * missing responsible business unit (affected / activity_subject ignored).
 */
export function isSignalMissingResponsibleClassification(signal: {
  responsible_business_unit_id?: string | null
}): boolean {
  return signal.responsible_business_unit_id == null
}
