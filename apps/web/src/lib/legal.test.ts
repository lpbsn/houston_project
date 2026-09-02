import { describe, expect, it } from 'vitest'

import { privacyPolicyContent } from '@/features/landing/content'

import {
  CURRENT_AI_CONSENT_VERSION,
  CURRENT_TERMS_VERSION,
  PUBLIC_PRIVACY_POLICY_URL,
  PUBLIC_TERMS_URL,
  isAiConsentRequired,
  isTermsAcceptanceRequired,
} from './legal'

describe('legal constants', () => {
  it('pins public URLs and current versions', () => {
    expect(PUBLIC_PRIVACY_POLICY_URL).toBe('https://spore-os.com/politique-de-confidentialite/')
    expect(PUBLIC_TERMS_URL).toBe('https://spore-os.com/conditions-d-utilisation/')
    expect(CURRENT_TERMS_VERSION).toBe('cgu-v1')
    expect(CURRENT_AI_CONSENT_VERSION).toBe('openai-v1')
    expect(isTermsAcceptanceRequired({ code: 'terms_acceptance_required' })).toBe(true)
    expect(isAiConsentRequired({ code: 'ai_consent_required' })).toBe(true)
  })

  it('keeps analytics pattern classification inside openai-v1 disclosure copy', () => {
    const openaiSection = privacyPolicyContent.sections.find(
      (section) => section.title === 'Intelligence artificielle (OpenAI)',
    )
    const joined = openaiSection?.paragraphs.join(' ') ?? ''
    expect(joined).toMatch(/openai-v1/)
    expect(joined).toMatch(/classement analytics/)
    expect(joined).not.toMatch(/hors du consentement/)
  })
})
