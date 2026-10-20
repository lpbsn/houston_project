// @vitest-environment jsdom

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen } from '@testing-library/react'
import { createElement } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { BrainAnalysisDetail } from '../api'
import { BrainAnalysisPanel } from './brain-analysis-panel'

vi.mock('../api', async () => {
  const actual = await vi.importActual<typeof import('../api')>('../api')
  return {
    ...actual,
    cancelBrainAnalysis: vi.fn(),
    cancelBrainFollowUp: vi.fn(),
    createBrainFollowUp: vi.fn(),
  }
})

function analysis(overrides: Partial<BrainAnalysisDetail>): BrainAnalysisDetail {
  return {
    id: 'analysis-1',
    status: 'completed',
    failure_code: '',
    failure_message: '',
    author: { id: 'user-1', name: 'Camille' },
    created_at: '2026-03-08T12:00:00Z',
    reporting: {
      id: 'reporting-1',
      original_filename: 'semaine.csv',
      period_start: '2026-03-01',
      period_end: '2026-03-08',
    },
    qualification: null,
    investigation_succeeded: null,
    claimed_at: null,
    result: null,
    dossier: null,
    searches: [],
    messages: [],
    older_message_count: 0,
    suggestions: [],
    evaluations: [],
    mechanisms: [],
    ...overrides,
  }
}

function renderPanel(value: BrainAnalysisDetail) {
  const client = new QueryClient()
  render(
    createElement(
      QueryClientProvider,
      { client },
      createElement(BrainAnalysisPanel, {
        establishmentId: 'est-1',
        analysis: value,
        sources: [],
        onChanged: () => undefined,
        onOpenAnalysis: () => undefined,
        onPrepareReanalysis: () => undefined,
      }),
    ),
  )
}

describe('BrainAnalysisPanel investigation states', () => {
  afterEach(() => {
    cleanup()
  })

  it('shows a factual reading as a reading, not a successful analysis', () => {
    renderPanel(
      analysis({
        qualification: 'factual_reading',
        investigation_succeeded: false,
        result: {
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
          cited: [
            {
              source_id: 's-01',
              label: 'Service midi',
              pole: 'Restauration',
              disposition: 'cited',
            },
          ],
          examined_not_cited: [
            {
              source_id: 's-03',
              label: 'Plan salle',
              pole: 'Restauration',
              disposition: 'examined_not_cited',
            },
          ],
          discovered_not_examined: [{ source_id: 's-02', pole: 'Hebergement' }],
        },
      }),
    )

    expect(screen.getAllByText('Lecture factuelle').length).toBeGreaterThan(0)
    expect(screen.getByText(/Ce n'est pas une analyse réussie/)).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Cités' })).toBeTruthy()
    expect(screen.getByText('Service midi — Restauration')).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Examinés, non cités' })).toBeTruthy()
    expect(screen.getByText('Plan salle — Restauration')).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Découverts, non examinés' })).toBeTruthy()
    expect(screen.getByText('s-02 — Hebergement')).toBeTruthy()
    expect(screen.queryByText(/Calcul vérifié/)).toBeNull()
  })

  it('keeps a completed lot result on the existing result section', () => {
    renderPanel(
      analysis({
        result: {
          schema_version: 'brain_analysis_v1',
          subjects: [{ key: 'ca', statement: 'Stable', limits: [], gaps: [] }],
          coverage: [],
          limits: [],
        },
      }),
    )

    expect(screen.getByText('Terminée')).toBeTruthy()
    expect(screen.getByText('Stable')).toBeTruthy()
    expect(screen.queryByText('Lecture factuelle')).toBeNull()
    expect(screen.queryByRole('heading', { name: 'Cités' })).toBeNull()
  })
})
