import { describe, expect, it } from 'vitest'

import {
  formatFunctionalStatus,
  formatResourceStatus,
  functionalStatusTone,
  resourceStatusTone,
} from './functional-status'

describe('platform status mapping', () => {
  it('maps functional statuses to labels and tones', () => {
    expect(formatFunctionalStatus('activated')).toBe('Activé')
    expect(functionalStatusTone('activated')).toBe('success')
    expect(formatFunctionalStatus('in_progress')).toBe('En cours')
    expect(functionalStatusTone('in_progress')).toBe('info')
    expect(functionalStatusTone('waiting_acceptance')).toBe('attention')
    expect(functionalStatusTone('ready_to_complete')).toBe('action')
    expect(functionalStatusTone('error')).toBe('problem')
  })

  it('maps resource statuses independently of color-only cues', () => {
    expect(formatResourceStatus('active')).toBe('Actif')
    expect(formatResourceStatus('draft')).toBe('Brouillon')
    expect(resourceStatusTone('active')).toBe('success')
    expect(resourceStatusTone('draft')).toBe('info')
    expect(resourceStatusTone('suspended')).toBe('attention')
    expect(resourceStatusTone('archived')).toBe('problem')
    expect(formatResourceStatus('unknown_status')).toBe('unknown_status')
  })
})
