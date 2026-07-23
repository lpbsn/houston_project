export const ESTABLISHMENT_APP_HOME_PATH = '/reporting'

export type OpenEstablishmentAppResult =
  | { kind: 'needs_switch'; establishmentId: string; path: string }
  | { kind: 'already_selected'; path: string }

export function planOpenEstablishmentApp({
  targetEstablishmentId,
  activeEstablishmentId,
}: {
  targetEstablishmentId: string
  activeEstablishmentId: string | null | undefined
}): OpenEstablishmentAppResult {
  const path = ESTABLISHMENT_APP_HOME_PATH
  if (activeEstablishmentId === targetEstablishmentId) {
    return { kind: 'already_selected', path }
  }
  return { kind: 'needs_switch', establishmentId: targetEstablishmentId, path }
}
