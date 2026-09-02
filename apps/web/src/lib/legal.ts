export const PUBLIC_PRIVACY_POLICY_URL =
  'https://spore-os.com/politique-de-confidentialite/' as const
export const PUBLIC_TERMS_URL = 'https://spore-os.com/conditions-d-utilisation/' as const
export const PUBLIC_LEGAL_NOTICE_URL = 'https://spore-os.com/mentions-legales/' as const
export const PUBLIC_ACCOUNT_DELETION_URL = 'https://spore-os.com/supprimer-compte/' as const

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
