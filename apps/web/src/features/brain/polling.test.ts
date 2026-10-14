import { describe, expect, it } from 'vitest'

import { BRAIN_POLL_INTERVAL_MS, brainPollInterval } from './polling'

describe('brainPollInterval', () => {
  it('polls while an analysis or a follow-up is queued or running', () => {
    expect(
      brainPollInterval({ visible: true, accessLost: false, statuses: ['completed', 'running'] }),
    ).toBe(BRAIN_POLL_INTERVAL_MS)
    expect(
      brainPollInterval({ visible: true, accessLost: false, statuses: ['queued'] }),
    ).toBe(BRAIN_POLL_INTERVAL_MS)
  })

  it('stops when the tracked work is terminal, the page is gone, or access is lost', () => {
    expect(
      brainPollInterval({
        visible: true,
        accessLost: false,
        statuses: ['completed', 'failed', 'canceled', null],
      }),
    ).toBe(false)
    expect(
      brainPollInterval({ visible: false, accessLost: false, statuses: ['running'] }),
    ).toBe(false)
    expect(
      brainPollInterval({ visible: true, accessLost: true, statuses: ['running'] }),
    ).toBe(false)
  })
})
