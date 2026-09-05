export const PUBLIC_PRIVACY_POLICY_URL =
  'https://spore-os.com/politique-de-confidentialite/' as const
export const PUBLIC_TERMS_URL = 'https://spore-os.com/conditions-d-utilisation/' as const
export const PUBLIC_LEGAL_NOTICE_URL = 'https://spore-os.com/mentions-legales/' as const
export const PUBLIC_ACCOUNT_DELETION_URL = 'https://spore-os.com/supprimer-compte/' as const
export const PUBLIC_SUPPORT_URL = 'https://spore-os.com/support/' as const
export const PUBLIC_MARKETING_URL = 'https://spore-os.com/' as const

export const CURRENT_TERMS_VERSION = 'cgu-v1' as const
export const CURRENT_AI_CONSENT_VERSION = 'openai-v1' as const

export const TERMS_ACCEPTANCE_REQUIRED_CODE = 'terms_acceptance_required' as const
export const AI_CONSENT_REQUIRED_CODE = 'ai_consent_required' as const

export function isTermsAcceptanceRequired(error: { code?: string | null }): boolean {
  return error.code === TERMS_ACCEPTANCE_REQUIRED_CODE
}

export function isAiConsentRequired(error: { code?: string | null }): boolean {
  return error.code === AI_CONSENT_REQUIRED_CODE
}

export type AiConsentStatus = 'undecided' | 'granted' | 'declined'

export const OBSERVATION_REQUIRES_AI_CONSENT_MESSAGE =
  'Activez le traitement OpenAI dans Général pour envoyer une observation.' as const

export function readAiConsentStatus(
  user: { ai_consent_status?: string | null } | null | undefined,
): AiConsentStatus {
  if (
    user?.ai_consent_status === 'granted' ||
    user?.ai_consent_status === 'declined' ||
    user?.ai_consent_status === 'undecided'
  ) {
    return user.ai_consent_status
  }
  return 'undecided'
}

export function isLegalError(error: unknown): boolean {
  if (!error || typeof error !== 'object') {
    return false
  }
  const code = 'code' in error && typeof error.code === 'string' ? error.code : null
  if (!code) {
    return false
  }
  return isTermsAcceptanceRequired({ code }) || isAiConsentRequired({ code })
}
