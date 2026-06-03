import { describe, expect, it } from 'vitest'

import {
  formatProcessingSuccessHeadline,
  formatSignalSummaryLine,
  shouldShowProcessingSignalList,
} from './processing-status-popup'

describe('processing-status-popup', () => {
  it('formats success headline for two signals created', () => {
    expect(formatProcessingSuccessHeadline(2, 'signal_created')).toBe(
      '2 signaux créés ou mis à jour',
    )
  })

  it('formats success headline for one signal updated', () => {
    expect(formatProcessingSuccessHeadline(1, 'signal_updated')).toBe('1 signal mis à jour')
  })

  it('returns null headline when no feed navigation', () => {
    expect(formatProcessingSuccessHeadline(0, 'no_signal_created')).toBeNull()
    expect(formatProcessingSuccessHeadline(2, 'analysis_failed')).toBeNull()
  })

  it('formats signal summary with taxonomy and location', () => {
    const line = formatSignalSummaryLine({
      id: '00000000-0000-0000-0000-000000000001',
      title: "Lumière clignote à l'entrée",
      operational_module_key: 'restaurant',
      operational_module_label: 'Restaurant',
      operational_domain_key: 'restaurant__salle',
      operational_domain_label: 'Salle',
      operational_subject_key: 'restaurant__salle__maintenance',
      operational_subject_label: 'Maintenance',
      location_text: 'Entrée restaurant',
    })
    expect(line).toContain('Restaurant')
    expect(line).toContain('Entrée restaurant')
    expect(line).not.toContain('mojito')
  })

  it('shows signal list only for terminal success ux statuses', () => {
    expect(shouldShowProcessingSignalList('signal_created')).toBe(true)
    expect(shouldShowProcessingSignalList('signal_updated')).toBe(true)
    expect(shouldShowProcessingSignalList('no_signal_created')).toBe(false)
    expect(shouldShowProcessingSignalList('analysis_failed')).toBe(false)
  })
})
