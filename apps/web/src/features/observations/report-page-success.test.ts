import { describe, expect, it } from 'vitest'

import {
  getProcessingUxLabel,
  shouldShowSignalFeedNavigation,
} from './processing-status-labels'
import { formatProcessingSuccessHeadline } from './processing-status-popup'

describe('report-page success state', () => {
  it('shows feed navigation only for signal_created ux status', () => {
    expect(shouldShowSignalFeedNavigation('signal_created')).toBe(true)
    expect(shouldShowSignalFeedNavigation('no_signal_created')).toBe(false)
    expect(shouldShowSignalFeedNavigation('analysis_failed')).toBe(false)
  })

  it('uses feed-only path for optional CTA', () => {
    const allowedPath = '/signals'
    expect(allowedPath).toBe('/signals')
    expect(allowedPath).not.toMatch(/\/signals\/[0-9a-f-]{36}$/i)
  })

  it('does not show feed CTA copy for no_signal_created or analysis_failed', () => {
    expect(getProcessingUxLabel('no_signal_created')).not.toContain(
      'liste des signaux a été mise à jour',
    )
  })

  it('formats popup headline from signal count without detail paths', () => {
    expect(formatProcessingSuccessHeadline(2, 'signal_created')).toBe(
      '2 signaux créés ou mis à jour',
    )
  })
})
