// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, render } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { useTrackObservation } from '@/features/observations/components/observation-processing-tracker-provider'
import {
  applyObservationPipelineStatusUpdate,
  __resetObservationProcessingTrackerStoreForTests,
  trackObservation,
} from '@/features/observations/lib/observation-processing-tracker-store'

function Probe({ onRender }: { onRender: () => void }) {
  const track = useTrackObservation()
  onRender()
  // Ensure the stable action is used (no subscription to banner state).
  void track
  return createElement('div', { 'data-testid': 'probe' })
}

describe('useTrackObservation render isolation', () => {
  afterEach(() => {
    cleanup()
    __resetObservationProcessingTrackerStoreForTests()
  })

  it('does not re-render origin pages when pipeline status updates', () => {
    let renderCount = 0
    render(createElement(Probe, { onRender: () => { renderCount += 1 } }))
    const initial = renderCount

    trackObservation({
      observationId: 'obs-1',
      establishmentId: 'est-1',
      authorMembershipId: 'mem-1',
      origin: 'direct_report',
      submittedAt: '2026-07-21T10:00:00.000Z',
    })
    applyObservationPipelineStatusUpdate({
      observationId: 'obs-1',
      status: 'processing',
      uxStatus: 'analysis_processing',
      processedAt: null,
      createdCount: 0,
      updatedCount: 0,
      signalIds: [],
    })
    applyObservationPipelineStatusUpdate({
      observationId: 'obs-1',
      status: 'processed',
      uxStatus: 'signal_created',
      processedAt: '2026-07-21T10:01:00.000Z',
      createdCount: 1,
      updatedCount: 0,
      signalIds: ['sig-1'],
    })

    expect(renderCount).toBe(initial)
  })
})
