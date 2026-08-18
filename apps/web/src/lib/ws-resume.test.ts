import { describe, expect, it } from 'vitest'

import { shouldResumeWsConnection } from './ws-resume'

describe('shouldResumeWsConnection', () => {
  it('does not resume when the channel is disabled', () => {
    expect(
      shouldResumeWsConnection({
        enabled: false,
        resumeBlocked: false,
        force: true,
        isConnected: false,
      }),
    ).toBe(false)
  })

  it('does not resume after an access close that blocks resume', () => {
    expect(
      shouldResumeWsConnection({
        enabled: true,
        resumeBlocked: true,
        force: true,
        isConnected: false,
      }),
    ).toBe(false)
  })

  it('resumes a disconnected channel on visibility or network return', () => {
    expect(
      shouldResumeWsConnection({
        enabled: true,
        resumeBlocked: false,
        force: false,
        isConnected: false,
      }),
    ).toBe(true)
  })

  it('does not resume a connected channel on visibility or network return', () => {
    expect(
      shouldResumeWsConnection({
        enabled: true,
        resumeBlocked: false,
        force: false,
        isConnected: true,
      }),
    ).toBe(false)
  })

  it('force-resumes a connected channel on native foreground', () => {
    expect(
      shouldResumeWsConnection({
        enabled: true,
        resumeBlocked: false,
        force: true,
        isConnected: true,
      }),
    ).toBe(true)
  })
})
