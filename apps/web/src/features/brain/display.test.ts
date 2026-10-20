import { describe, expect, it } from 'vitest'

import { analysisHistoryLabel, readAnalysisResult, readInvestigationResult } from './display'

describe('investigation presentation', () => {
  it('keeps a lot result on the treatment label', () => {
    expect(analysisHistoryLabel('completed', null, null)).toBe('Terminée')
    expect(
      readAnalysisResult({
        schema_version: 'brain_analysis_v1',
        subjects: [{ key: 'ca', statement: 'Stable', limits: [], gaps: [] }],
      })?.subjects[0]?.key,
    ).toBe('ca')
  })

  it('does not present a factual reading as a successful analysis', () => {
    expect(analysisHistoryLabel('completed', 'factual_reading', false)).toBe('Lecture factuelle')
    expect(analysisHistoryLabel('completed', 'refused', false)).toBe('Analyse refusée')
    expect(analysisHistoryLabel('failed', null, null)).toBe('Échec')
    const view = readInvestigationResult({
      schema_version: 'brain_investigation_v3',
      qualification: 'factual_reading',
      investigation_succeeded: false,
      subjects: [
        {
          key: 'frequentation',
          statement: 'Le chiffre est rapporté.',
          examined: true,
          calculations: [{ label: 'montant', published_value: '10', verified: false }],
        },
      ],
      cited: [{ source_id: 's-01', label: 'Service midi', pole: 'Restauration', disposition: 'cited' }],
      examined_not_cited: [
        { source_id: 's-03', label: 'Plan salle', disposition: 'examined_not_cited' },
      ],
      discovered_not_examined: [{ source_id: 's-02', pole: 'Hebergement' }],
    })
    expect(view?.investigationSucceeded).toBe(false)
    expect(view?.subjects[0]?.calculations).toEqual([])
    expect(view?.cited.map((item) => item.sourceId)).toEqual(['s-01'])
    expect(view?.examinedNotCited.map((item) => item.sourceId)).toEqual(['s-03'])
    expect(view?.discoveredNotExamined[0]?.sourceId).toBe('s-02')
    expect(view?.discoveredNotExamined[0]?.disposition).toBe('discovered_not_examined')
    expect(readAnalysisResult({ schema_version: 'brain_investigation_v3', subjects: [] })).toBeNull()
  })

  it('names a verified partial analysis as partial', () => {
    expect(analysisHistoryLabel('completed', 'partial', true)).toBe('Analyse partielle')
    expect(analysisHistoryLabel('completed', 'complete', true)).toBe('Analyse complète')
  })
})
