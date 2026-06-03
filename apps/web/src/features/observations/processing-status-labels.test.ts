import { describe, expect, it } from 'vitest'

import {
  getProcessingUxLabel,
  isTerminalProcessingStatus,
  shouldInvalidateSignalFeedOnTerminal,
  shouldPollProcessingStatus,
  shouldShowSignalFeedNavigation,
} from './processing-status-labels'

describe('processing-status-labels', () => {
  it('maps ux_status codes to French labels', () => {
    expect(getProcessingUxLabel('analysis_queued')).toBe('Analyse en attente')
    expect(getProcessingUxLabel('analysis_processing')).toBe('Analyse en cours')
    expect(getProcessingUxLabel('analysis_retrying')).toBe('Nouvelle tentative d’analyse')
    expect(getProcessingUxLabel('signal_created')).toBe(
      'Signal créé. Le feed a été mis à jour.',
    )
    expect(getProcessingUxLabel('signal_updated')).toBe(
      'Signal mis à jour. Le feed a été mis à jour.',
    )
    expect(getProcessingUxLabel('no_signal_created')).toBe(
      'Observation enregistrée, aucun signal actionnable détecté',
    )
    expect(getProcessingUxLabel('analysis_failed')).toBe('Analyse temporairement indisponible')
  })

  it('detects terminal processing statuses', () => {
    expect(isTerminalProcessingStatus('processed')).toBe(true)
    expect(isTerminalProcessingStatus('failed')).toBe(true)
    expect(isTerminalProcessingStatus('queued')).toBe(false)
    expect(isTerminalProcessingStatus('processing')).toBe(false)
  })

  it('polls until terminal status', () => {
    expect(shouldPollProcessingStatus(undefined)).toBe(true)
    expect(shouldPollProcessingStatus('queued')).toBe(true)
    expect(shouldPollProcessingStatus('processing')).toBe(true)
    expect(shouldPollProcessingStatus('processed')).toBe(false)
    expect(shouldPollProcessingStatus('failed')).toBe(false)
  })

  it('shows signal feed navigation only when a signal was created or updated', () => {
    expect(shouldShowSignalFeedNavigation('signal_created')).toBe(true)
    expect(shouldShowSignalFeedNavigation('signal_updated')).toBe(true)
    expect(shouldShowSignalFeedNavigation('no_signal_created')).toBe(false)
    expect(shouldShowSignalFeedNavigation('analysis_failed')).toBe(false)
    expect(shouldShowSignalFeedNavigation('analysis_queued')).toBe(false)
  })

  it('invalidates signal feed only on processed terminal outcomes with feed updates', () => {
    expect(shouldInvalidateSignalFeedOnTerminal('processed', 'signal_created')).toBe(true)
    expect(shouldInvalidateSignalFeedOnTerminal('processed', 'signal_updated')).toBe(true)
    expect(shouldInvalidateSignalFeedOnTerminal('processed', 'no_signal_created')).toBe(false)
    expect(shouldInvalidateSignalFeedOnTerminal('failed', 'analysis_failed')).toBe(false)
    expect(shouldInvalidateSignalFeedOnTerminal('queued', 'analysis_queued')).toBe(false)
  })

  it('does not use signal_ids or feed fallbacks for navigation helpers', () => {
    expect(shouldShowSignalFeedNavigation('signal_created')).toBe(true)
    expect(getProcessingUxLabel('signal_created')).not.toContain('/signals/')
  })
})
