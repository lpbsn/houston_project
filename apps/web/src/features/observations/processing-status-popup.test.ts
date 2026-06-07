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

  it('formats signal summary with business unit taxonomy and location', () => {
    const line = formatSignalSummaryLine({
      id: '00000000-0000-0000-0000-000000000001',
      title: "Lumière clignote à l'entrée",
      affected_business_unit_key: 'restaurant',
      affected_business_unit_label: 'Restaurant',
      responsible_business_unit_key: 'maintenance',
      responsible_business_unit_label: 'Maintenance',
      activity_subject_key: 'electricite',
      activity_subject_label: 'Électricité',
      location_text: 'Entrée restaurant',
    })
    expect(line).toContain('Maintenance')
    expect(line).toContain('Électricité')
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
