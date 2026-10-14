export const WORK_STATUS_LABELS: Record<string, string> = {
  queued: 'En attente',
  running: 'Analyse en cours',
  completed: 'Terminée',
  failed: 'Échec',
  canceled: 'Annulée',
}

export const PURPOSE_LABELS: Record<string, string> = {
  explain: 'Explication',
  hypothesis: 'Hypothèse',
  correction: 'Correction',
  new_fact: 'Fait nouveau',
  new_document: 'Nouveau document',
}

export const OUTCOME_LABELS: Record<string, string> = {
  reached: 'Atteint',
  not_reached: 'Non atteint',
  non_evaluable: 'Non évaluable',
  qualitative: 'Qualitatif',
}

export const OBJECTIVE_DECISION_LABELS: Record<string, string> = {
  recorded: 'Enregistré, sans décision humaine',
  accepted: 'Accepté',
  modified: 'Modifié',
  refused: 'Refusé',
}

const DECLARATION_PURPOSES = new Set(['correction', 'new_fact', 'new_document'])

export function isDeclarationPurpose(purpose: string): boolean {
  return DECLARATION_PURPOSES.has(purpose)
}

export function workStatusLabel(status: string): string {
  return WORK_STATUS_LABELS[status] ?? status
}

function asRecord(value: unknown): Record<string, unknown> | null {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    return null
  }
  return value as Record<string, unknown>
}

function asString(value: unknown): string {
  return typeof value === 'string' ? value : ''
}

function asStringList(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return []
  }
  return value.filter((item): item is string => typeof item === 'string')
}

export type AnalysisSubjectView = {
  key: string
  statement: string
  interpretation: string
  orientation: string
  limits: string[]
  gaps: string[]
  contradictions: string[]
}

export type AnalysisResultView = {
  subjects: AnalysisSubjectView[]
  coverage: { pieceId: string; disposition: string; reason: string }[]
  limits: { code: string; message: string }[]
}

export function readAnalysisResult(value: unknown): AnalysisResultView | null {
  const record = asRecord(value)
  if (!record || !Array.isArray(record.subjects)) {
    return null
  }
  const subjects = record.subjects.flatMap((item) => {
    const subject = asRecord(item)
    if (!subject) {
      return []
    }
    return [
      {
        key: asString(subject.key),
        statement: asString(subject.statement),
        interpretation: asString(subject.interpretation),
        orientation: asString(subject.orientation),
        limits: asStringList(subject.limits),
        gaps: asStringList(subject.gaps),
        contradictions: asStringList(subject.contradictions),
      },
    ]
  })
  const coverage = Array.isArray(record.coverage)
    ? record.coverage.flatMap((item) => {
        const entry = asRecord(item)
        if (!entry) {
          return []
        }
        return [
          {
            pieceId: asString(entry.piece_id),
            disposition: asString(entry.disposition),
            reason: asString(entry.reason),
          },
        ]
      })
    : []
  const limits = Array.isArray(record.limits)
    ? record.limits.flatMap((item) => {
        const entry = asRecord(item)
        if (!entry) {
          return []
        }
        return [{ code: asString(entry.code), message: asString(entry.message) }]
      })
    : []
  return { subjects, coverage, limits }
}

export type ReanalysisProposal = {
  proposed: boolean
  launched: boolean
  reason: string
  requiresNewReporting: boolean
  reportingId: string | null
  periodStart: string | null
  periodEnd: string | null
}

export type FollowUpResultView = {
  mode: string
  answer: string
  reanalysis: ReanalysisProposal | null
}

export function readFollowUpResult(value: unknown): FollowUpResultView | null {
  const record = asRecord(value)
  if (!record) {
    return null
  }
  const reanalysis = asRecord(record.reanalysis)
  return {
    mode: asString(record.mode),
    answer: asString(record.answer),
    reanalysis: reanalysis
      ? {
          proposed: reanalysis.proposed === true,
          launched: reanalysis.launched === true,
          reason: asString(reanalysis.reason),
          requiresNewReporting: reanalysis.requires_new_reporting === true,
          reportingId: typeof reanalysis.reporting_id === 'string' ? reanalysis.reporting_id : null,
          periodStart: typeof reanalysis.period_start === 'string' ? reanalysis.period_start : null,
          periodEnd: typeof reanalysis.period_end === 'string' ? reanalysis.period_end : null,
        }
      : null,
  }
}

export function declarationApplied(value: unknown): boolean | null {
  const record = asRecord(value)
  if (!record || typeof record.applied !== 'boolean') {
    return null
  }
  return record.applied
}

export type FrozenSource = {
  itemId: string
  category: string
  title: string
  sourceId: string | null
  periodStatusUnreconstructable: boolean
}

export function readFrozenSource(value: unknown): FrozenSource | null {
  const record = asRecord(value)
  if (!record) {
    return null
  }
  const locators = Array.isArray(record.locators) ? record.locators : []
  const sourceId = locators
    .map((locator) => asRecord(locator)?.source_id)
    .find((item): item is string => typeof item === 'string' && item.length > 0)
  const periodStatuses = [record.status_at_period_start, record.status_at_period_end]
  return {
    itemId: asString(record.item_id),
    category: asString(record.category),
    title: asString(record.title) || asString(record.label) || asString(record.item_id),
    sourceId: sourceId ?? null,
    periodStatusUnreconstructable: periodStatuses.some((status) => status === 'not_reconstructable'),
  }
}

export function liveSourceHref(
  establishmentId: string,
  category: string,
  sourceId: string | null,
): string | null {
  if (!sourceId) {
    return null
  }
  if (category === 'signal') {
    return `/e/${establishmentId}/signals/${sourceId}`
  }
  if (category === 'execution') {
    return `/e/${establishmentId}/execution/${sourceId}`
  }
  return null
}

export function errorDetail(error: unknown): string {
  if (error instanceof Error && error.message) {
    return error.message
  }
  return 'Une erreur est survenue.'
}
