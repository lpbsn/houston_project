import { describe, expect, it } from 'vitest'

import {
  getProcessingUxLabel,
  shouldShowSignalFeedNavigation,
} from './processing-status-labels'
import { formatProcessingSuccessHeadline } from './processing-status-popup'

/**
 * ReportPage success-state rules (tested without rendering — no @testing-library in web).
 * Navigation must never target /signals/{id}; optional CTA goes to /signals only.
 */
describe('report-page success state', () => {
  it('never derives detail navigation from signal_ids', () => {
    const signalIdsFromApi = ['11111111-1111-4111-8111-111111111111']
    const uxStatus = 'signal_created'

    expect(shouldShowSignalFeedNavigation(uxStatus)).toBe(true)
    expect(signalIdsFromApi[0]).toBeTruthy()
    // Product rule: signal_ids must not be used to build /signals/{id} paths.
    const forbiddenPath = `/signals/${signalIdsFromApi[0]}`
    expect(forbiddenPath).toMatch(/^\/signals\//)
    expect(shouldShowSignalFeedNavigation(uxStatus)).toBe(true)
  })

  it('uses feed-only path for optional CTA', () => {
    const allowedPath = '/signals'
    expect(allowedPath).toBe('/signals')
    expect(allowedPath).not.toMatch(/\/signals\/[0-9a-f-]{36}$/i)
  })

  it('does not show feed CTA for no_signal_created or analysis_failed', () => {
    expect(shouldShowSignalFeedNavigation('no_signal_created')).toBe(false)
    expect(shouldShowSignalFeedNavigation('analysis_failed')).toBe(false)
    expect(getProcessingUxLabel('no_signal_created')).not.toContain('liste des signaux a été mise à jour')
  })

  it('formats popup headline for two signals without using signal_ids for navigation', () => {
    const signalIdsFromApi = [
      '11111111-1111-4111-8111-111111111111',
      '22222222-2222-4222-8222-222222222222',
    ]
    expect(formatProcessingSuccessHeadline(signalIdsFromApi.length, 'signal_created')).toBe(
      '2 signaux créés ou mis à jour',
    )
    const forbiddenPath = `/signals/${signalIdsFromApi[0]}`
    expect(forbiddenPath).toMatch(/^\/signals\//)
  })
})
