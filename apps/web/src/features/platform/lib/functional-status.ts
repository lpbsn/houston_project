export const FUNCTIONAL_STATUS_LABELS: Record<string, string> = {
  in_progress: 'En cours',
  waiting_acceptance: 'En attente d’acceptation',
  ready_to_complete: 'Prêt à finaliser',
  activated: 'Activé',
  error: 'Erreur',
}

export function formatFunctionalStatus(status: string | null | undefined): string {
  if (!status) {
    return '—'
  }
  return FUNCTIONAL_STATUS_LABELS[status] ?? status
}
