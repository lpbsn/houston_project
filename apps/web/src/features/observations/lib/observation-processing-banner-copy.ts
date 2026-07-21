import type { TerminalStatusSnapshot } from './observation-processing-tracker-types'

function pluralizeObservation(count: number, singular: string, plural: string): string {
  return count === 1 ? singular : plural
}

export function formatTerminalBannerLabel(terminal: TerminalStatusSnapshot): string {
  if (terminal.status === 'failed') {
    return 'Observation enregistrée, mais son analyse a échoué'
  }

  const created = terminal.createdCount
  const updated = terminal.updatedCount

  if (created === 0 && updated === 0) {
    return 'Observation enregistrée — aucun élément opérationnel détecté'
  }

  const parts: string[] = []
  if (created > 0) {
    parts.push(
      `${created} ${pluralizeObservation(created, 'observation créée', 'observations créées')}`,
    )
  }
  if (updated > 0) {
    parts.push(
      `${updated} ${pluralizeObservation(
        updated,
        'observation existante mise à jour',
        'observations existantes mises à jour',
      )}`,
    )
  }
  return parts.join(' · ')
}

export function formatProgressBannerLabel(
  pipelineStatus: string | null,
  inProgressCount: number,
): string {
  if (inProgressCount > 1) {
    return `${inProgressCount} observations en cours d’analyse`
  }
  if (pipelineStatus === 'queued') {
    return 'Analyse en attente'
  }
  if (pipelineStatus === 'retrying') {
    return 'Nouvelle tentative d’analyse'
  }
  return 'Analyse en cours'
}

export function resolveTerminalBannerNavigation(
  terminal: TerminalStatusSnapshot,
): string | null {
  if (terminal.status === 'failed') {
    return '/reporting'
  }
  const total = terminal.createdCount + terminal.updatedCount
  if (total === 0) {
    return null
  }
  if (total === 1 && terminal.signalIds.length === 1) {
    return `/signals/${terminal.signalIds[0]}`
  }
  if (total === 1 && terminal.signalIds.length === 0) {
    return '/signals'
  }
  return '/signals'
}

export function shouldInvalidateSignalFeedFromTerminal(
  terminal: TerminalStatusSnapshot,
): boolean {
  return (
    terminal.status === 'processed' &&
    (terminal.createdCount > 0 || terminal.updatedCount > 0)
  )
}
