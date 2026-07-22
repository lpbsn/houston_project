export type DraftOnboardingResumeFields = {
  can_continue_onboarding?: boolean | null
  onboarding_session_id?: string | null
}

export function canResumeDraftOnboarding(establishment: DraftOnboardingResumeFields): boolean {
  return (
    establishment.can_continue_onboarding === true &&
    typeof establishment.onboarding_session_id === 'string' &&
    establishment.onboarding_session_id.length > 0
  )
}
