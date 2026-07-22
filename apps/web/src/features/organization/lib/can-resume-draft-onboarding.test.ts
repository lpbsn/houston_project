import { describe, expect, it } from 'vitest'

import { canResumeDraftOnboarding } from './can-resume-draft-onboarding'

describe('canResumeDraftOnboarding', () => {
  it('requires both can_continue_onboarding and a session id', () => {
    expect(
      canResumeDraftOnboarding({
        can_continue_onboarding: true,
        onboarding_session_id: 'session-1',
      }),
    ).toBe(true)
  })

  it('rejects when session is missing', () => {
    expect(
      canResumeDraftOnboarding({
        can_continue_onboarding: true,
        onboarding_session_id: null,
      }),
    ).toBe(false)
  })

  it('rejects when cannot continue', () => {
    expect(
      canResumeDraftOnboarding({
        can_continue_onboarding: false,
        onboarding_session_id: 'session-1',
      }),
    ).toBe(false)
  })
})
