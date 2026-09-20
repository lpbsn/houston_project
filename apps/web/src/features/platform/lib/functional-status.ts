export type StatusTone = 'success' | 'info' | 'attention' | 'action' | 'problem'

export const FUNCTIONAL_STATUS_LABELS: Record<string, string> = {
  in_progress: 'En cours',
  waiting_acceptance: 'En attente d’acceptation',
  ready_to_complete: 'Prêt à finaliser',
  activated: 'Activé',
  error: 'Erreur',
}

const FUNCTIONAL_STATUS_TONES: Record<string, StatusTone> = {
  activated: 'success',
  in_progress: 'info',
  waiting_acceptance: 'attention',
  ready_to_complete: 'action',
  error: 'problem',
}

export const RESOURCE_STATUS_LABELS: Record<string, string> = {
  active: 'Actif',
  draft: 'Brouillon',
  suspended: 'Suspendu',
  archived: 'Archivé',
  invited: 'Invité',
  pending: 'En attente',
  deactivated: 'Désactivé',
  anonymized: 'Anonymisé',
}

const RESOURCE_STATUS_TONES: Record<string, StatusTone> = {
  active: 'success',
  activated: 'success',
  draft: 'info',
  pending: 'info',
  in_progress: 'info',
  invited: 'attention',
  waiting_acceptance: 'attention',
  suspended: 'attention',
  ready_to_complete: 'action',
  archived: 'problem',
  deactivated: 'problem',
  anonymized: 'problem',
  error: 'problem',
  failed: 'problem',
}

export function formatFunctionalStatus(status: string | null | undefined): string {
  if (!status) {
    return '—'
  }
  return FUNCTIONAL_STATUS_LABELS[status] ?? status
}

export function functionalStatusTone(status: string | null | undefined): StatusTone {
  if (!status) {
    return 'info'
  }
  return FUNCTIONAL_STATUS_TONES[status] ?? 'info'
}

export function formatResourceStatus(status: string | null | undefined): string {
  if (!status) {
    return '—'
  }
  return RESOURCE_STATUS_LABELS[status] ?? status
}

export function resourceStatusTone(status: string | null | undefined): StatusTone {
  if (!status) {
    return 'info'
  }
  return RESOURCE_STATUS_TONES[status] ?? FUNCTIONAL_STATUS_TONES[status] ?? 'info'
}

export function formatMembershipRole(role: string | null | undefined): string {
  if (!role) {
    return '—'
  }
  const labels: Record<string, string> = {
    owner: 'Owner',
    director: 'Director',
    manager: 'Manager',
    staff: 'Staff',
  }
  return labels[role] ?? role
}
