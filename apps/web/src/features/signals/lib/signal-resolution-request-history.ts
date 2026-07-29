export type ResolutionRequestEventType =
  | 'created'
  | 'approved'
  | 'rejected'
  | 'canceled'

export type ResolutionRequestHistoryEvent = {
  request_id: string
  event_type: ResolutionRequestEventType
  occurred_at: string
  actor_display_name: string | null
}

export function formatResolutionRequestEventDate(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) {
    return ''
  }
  return new Intl.DateTimeFormat('fr-FR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

export function formatResolutionRequestEventLabel(
  event: Pick<ResolutionRequestHistoryEvent, 'event_type' | 'actor_display_name'>,
): string {
  const actor = event.actor_display_name?.trim() || null
  switch (event.event_type) {
    case 'created':
      return actor
        ? `Demande de résolution en attente — Envoyée par ${actor}`
        : 'Demande de résolution en attente'
    case 'approved':
      return actor
        ? `Demande de résolution validée — Validée par ${actor}`
        : 'Demande de résolution validée'
    case 'rejected':
      return actor
        ? `Demande de résolution refusée — Refusée par ${actor}`
        : 'Demande de résolution refusée'
    case 'canceled':
      return actor
        ? `Demande de résolution annulée — Annulée par ${actor}`
        : 'Demande de résolution annulée — Annulée automatiquement'
    default:
      return 'Demande de résolution'
  }
}

export function formatResolutionRequestHistoryLine(
  event: ResolutionRequestHistoryEvent,
): string {
  const dateLabel = formatResolutionRequestEventDate(event.occurred_at)
  const eventLabel = formatResolutionRequestEventLabel(event)
  return dateLabel ? `${dateLabel} — ${eventLabel}` : eventLabel
}
