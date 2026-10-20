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

export const QUALIFICATION_LABELS: Record<string, string> = {
  complete: 'Analyse complète',
  partial: 'Analyse partielle',
  factual_reading: 'Lecture factuelle',
  refused: 'Analyse refusée',
}

export function analysisHistoryLabel(
  status: string,
  qualification?: string | null,
  investigationSucceeded?: boolean | null,
): string {
  if (status !== 'completed' || !qualification) {
    return workStatusLabel(status)
  }
  if (qualification === 'factual_reading' || qualification === 'refused') {
    return QUALIFICATION_LABELS[qualification]
  }
  if (investigationSucceeded === true && QUALIFICATION_LABELS[qualification]) {
    return QUALIFICATION_LABELS[qualification]
  }
  if (investigationSucceeded === false) {
    return QUALIFICATION_LABELS[qualification] ?? workStatusLabel(status)
  }
  return workStatusLabel(status)
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

function coverageItems(
  rows: unknown,
  identifiers: unknown,
  disposition: string,
): InvestigationCoverageItem[] {
  if (Array.isArray(rows)) {
    const parsed = rows.flatMap((item) => {
      if (typeof item === 'string') {
        return [{ sourceId: item, label: '', pole: '', disposition }]
      }
      const row = asRecord(item)
      if (!row) {
        return []
      }
      const sourceId = asString(row.source_id)
      if (!sourceId) {
        return []
      }
      return [
        {
          sourceId,
          label: asString(row.label),
          pole: asString(row.pole),
          disposition: asString(row.disposition) || disposition,
        },
      ]
    })
    if (parsed.length > 0) {
      return parsed
    }
  }
  return asStringList(identifiers).map((sourceId) => ({
    sourceId,
    label: '',
    pole: '',
    disposition,
  }))
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

export type InvestigationSubjectView = {
  key: string
  statement: string
  examined: boolean
  orientation: string
  justification: string
  limits: string[]
  gaps: string[]
  calculations: { label: string; value: string; verified: boolean }[]
  cited: InvestigationCoverageItem[]
  notExaminedIds: string[]
}

export type InvestigationCoverageItem = {
  sourceId: string
  label: string
  pole: string
  disposition: string
}

export type InvestigationResultView = {
  qualification: string
  investigationSucceeded: boolean
  subjects: InvestigationSubjectView[]
  examinedIds: string[]
  examinedNotCited: InvestigationCoverageItem[]
  cited: InvestigationCoverageItem[]
  discoveredNotExamined: InvestigationCoverageItem[]
  limits: { code: string; sourceId: string }[]
}

export function readInvestigationResult(value: unknown): InvestigationResultView | null {
  const record = asRecord(value)
  if (!record || record.schema_version !== 'brain_investigation_v3') {
    return null
  }
  const qualification = asString(record.qualification)
  if (!qualification) {
    return null
  }
  const subjects = Array.isArray(record.subjects)
    ? record.subjects.flatMap((item) => {
        const subject = asRecord(item)
        if (!subject) {
          return []
        }
        const calculations = Array.isArray(subject.calculations)
          ? subject.calculations.flatMap((entry) => {
              const calculation = asRecord(entry)
              if (!calculation || calculation.verified !== true) {
                return []
              }
              return [
                {
                  label: asString(calculation.label) || asString(calculation.operation),
                  value: asString(calculation.published_value),
                  verified: true,
                },
              ]
            })
          : []
        return [
          {
            key: asString(subject.key),
            statement: asString(subject.statement),
            examined: subject.examined === true,
            orientation: asString(subject.orientation),
            justification: asString(subject.justification),
            limits: asStringList(subject.limits),
            gaps: asStringList(subject.gaps),
            calculations,
            cited: coverageItems(subject.cited, subject.cited_ids, 'cited'),
            notExaminedIds: asStringList(subject.not_examined_ids),
          },
        ]
      })
    : []
  const discovered = coverageItems(
    record.discovered_not_examined,
    undefined,
    'discovered_not_examined',
  )
  const limits = Array.isArray(record.limits)
    ? record.limits.flatMap((item) => {
        const row = asRecord(item)
        if (!row) {
          return []
        }
        return [{ code: asString(row.code), sourceId: asString(row.source_id) }]
      })
    : []
  return {
    qualification,
    investigationSucceeded: record.investigation_succeeded === true,
    subjects,
    examinedIds: asStringList(record.examined_ids),
    examinedNotCited: coverageItems(record.examined_not_cited, undefined, 'examined_not_cited'),
    cited: coverageItems(record.cited, record.cited_ids, 'cited'),
    discoveredNotExamined: discovered,
    limits,
  }
}

export function readAnalysisResult(value: unknown): AnalysisResultView | null {
  const record = asRecord(value)
  if (!record || record.schema_version === 'brain_investigation_v3' || !Array.isArray(record.subjects)) {
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
