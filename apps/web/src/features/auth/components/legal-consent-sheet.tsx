import { useState } from 'react'

import { AuthApiError, acceptCurrentAiConsent, acceptCurrentTerms } from '@/features/auth/api'
import { TerrainBottomSheet } from '@/components/ui/terrain'
import { Button } from '@/components/ui/button'
import {
  PUBLIC_PRIVACY_POLICY_URL,
  PUBLIC_TERMS_URL,
  isAiConsentRequired,
  isTermsAcceptanceRequired,
} from '@/lib/legal'

type LegalConsentKind = 'terms' | 'ai' | null

export function legalConsentKindFromError(error: unknown): LegalConsentKind {
  if (!error || typeof error !== 'object') {
    return null
  }
  const code = 'code' in error && typeof error.code === 'string' ? error.code : null
  if (code && isTermsAcceptanceRequired({ code })) {
    return 'terms'
  }
  if (code && isAiConsentRequired({ code })) {
    return 'ai'
  }
  return null
}

type LegalConsentSheetProps = {
  kind: LegalConsentKind
  onClose: () => void
  onAccepted: () => void
}

export function LegalConsentSheet({ kind, onClose, onAccepted }: LegalConsentSheetProps) {
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (!kind) {
    return null
  }

  const isTerms = kind === 'terms'

  async function accept() {
    setPending(true)
    setError(null)
    try {
      if (isTerms) {
        await acceptCurrentTerms()
      } else {
        await acceptCurrentAiConsent()
      }
      onAccepted()
      onClose()
    } catch (caught) {
      setError(
        caught instanceof AuthApiError ? caught.message : 'Enregistrement impossible.',
      )
    } finally {
      setPending(false)
    }
  }

  return (
    <TerrainBottomSheet
      title={isTerms ? 'Conditions d’utilisation' : 'Traitement OpenAI'}
      open
      onClose={onClose}
    >
      <div className="space-y-3 text-sm text-[#5c5a54]">
        {isTerms ? (
          <p>
            Pour publier une observation, un commentaire ou un message visible par l’équipe,
            acceptez les{' '}
            <a href={PUBLIC_TERMS_URL} className="underline" target="_blank" rel="noreferrer">
              conditions d’utilisation
            </a>
            .
          </p>
        ) : (
          <p>
            La transcription, l’analyse d’observation et le classement analytics des signaux
            (titre, synthèse, focus) envoient ces données à OpenAI (version openai-v1). Les
            photos et le chat ne sont pas envoyés. Détails :{' '}
            <a
              href={PUBLIC_PRIVACY_POLICY_URL}
              className="underline"
              target="_blank"
              rel="noreferrer"
            >
              politique de confidentialité
            </a>
            .
          </p>
        )}
        {error ? <p className="text-[#E24B4A]">{error}</p> : null}
        <Button className="h-11 w-full rounded-xl" disabled={pending} onClick={() => void accept()}>
          {pending ? 'Enregistrement...' : isTerms ? 'Accepter' : 'Consentir'}
        </Button>
      </div>
    </TerrainBottomSheet>
  )
}
