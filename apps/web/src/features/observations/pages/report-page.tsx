import { useRef, useState } from 'react'
import { LoaderCircle, SendHorizonal } from 'lucide-react'
import { useReducedMotion } from 'framer-motion'

import { useAuth } from '@/app/auth-provider'
import { TerrainCard, TerrainErrorState, TerrainStickyFooter } from '@/components/ui/terrain'
import { Button } from '@/components/ui/button'
import { ReportPhotosSection } from '@/features/observations/components/report-photos-section'
import { ReportTextSection } from '@/features/observations/components/report-text-section'
import { trackObservation } from '@/features/observations/components/observation-processing-tracker-provider'
import { ObservationsApiError } from '@/features/observations/api'
import {
  useSubmitObservationComposeMutation,
  useTranscribeAudioMutation,
} from '@/features/observations/hooks'
import { useReportingComposeDraft } from '@/features/observations/lib/use-observation-compose-draft'
import {
  MAX_OBSERVATION_PHOTOS,
  OBSERVATION_TEXT_MAX_LENGTH,
  OBSERVATION_TEXT_MIN_LENGTH,
} from '@/features/observations/types'
import { LegalConsentSheet, legalConsentKindFromError } from '@/features/auth/components/legal-consent-sheet'
import { resolveApiErrorMessage } from '@/lib/error-message'
import { PUBLIC_PRIVACY_POLICY_URL } from '@/lib/legal'
import { useNetworkStatus } from '@/lib/network-status'
import { terrain, terrainBrandAction } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

export function ReportPage({ establishmentId: establishmentIdProp }: { establishmentId?: string | null } = {}) {
  const shouldReduceMotion = useReducedMotion()
  const auth = useAuth()
  const { isOnline } = useNetworkStatus()
  const establishmentId =
    establishmentIdProp ?? auth.bootstrap?.active_membership?.establishment_id ?? null
  const fromList = (auth.bootstrap?.memberships ?? []).find(
    (membership) =>
      membership.establishment_id === establishmentId && membership.status === 'active',
  )?.id
  const active = auth.bootstrap?.active_membership
  const authorMembershipId =
    fromList ?? (active?.establishment_id === establishmentId ? active.id : null) ?? null
  const { text, photos, setText, addPhoto, removePhoto, clear } =
    useReportingComposeDraft(establishmentId)

  const [formError, setFormError] = useState<string | null>(null)
  const [legalKind, setLegalKind] = useState<ReturnType<typeof legalConsentKindFromError>>(null)
  const [isRecording, setIsRecording] = useState(false)
  const [isTranscribing, setIsTranscribing] = useState(false)

  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])

  const transcribeMutation = useTranscribeAudioMutation(establishmentId)
  const submitMutation = useSubmitObservationComposeMutation(establishmentId)

  const isSubmitPending = submitMutation.isPending

  const trimmedText = text.trim()
  const textLength = trimmedText.length
  const canSubmit =
    textLength >= OBSERVATION_TEXT_MIN_LENGTH &&
    textLength <= OBSERVATION_TEXT_MAX_LENGTH &&
    isOnline &&
    !isSubmitPending &&
    !isTranscribing

  const resolveReportError = (error: unknown) =>
    resolveApiErrorMessage(error, ObservationsApiError, 'Une erreur est survenue.')

  const handlePhotoSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file || !establishmentId) {
      return
    }
    if (photos.length >= MAX_OBSERVATION_PHOTOS) {
      setFormError(`Limite : ${MAX_OBSERVATION_PHOTOS} photos maximum.`)
      return
    }

    setFormError(null)
    addPhoto(file)
  }

  const handleStartRecording = async () => {
    setFormError(null)
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream)
      chunksRef.current = []
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data)
        }
      }
      recorder.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop())
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || 'audio/webm' })
        if (blob.size === 0) {
          setFormError('Enregistrement audio trop court.')
          return
        }
        setIsTranscribing(true)
        try {
          const result = await transcribeMutation.mutateAsync({
            blob,
            fileName: 'observation-audio.webm',
          })
          setText(result.text.slice(0, OBSERVATION_TEXT_MAX_LENGTH))
        } catch (error) {
          const kind = legalConsentKindFromError(error)
          if (kind) {
            setLegalKind(kind)
          }
          setFormError(resolveReportError(error))
        } finally {
          setIsTranscribing(false)
        }
      }
      mediaRecorderRef.current = recorder
      recorder.start()
      setIsRecording(true)
    } catch {
      setFormError('Microphone indisponible. Saisissez le texte manuellement.')
    }
  }

  const handleStopRecording = () => {
    mediaRecorderRef.current?.stop()
    mediaRecorderRef.current = null
    setIsRecording(false)
  }

  const handleSubmit = async () => {
    setFormError(null)
    if (!canSubmit) {
      if (!trimmedText) {
        setFormError('Le texte est obligatoire (photo seule interdite).')
      } else if (textLength < OBSERVATION_TEXT_MIN_LENGTH) {
        setFormError(`Minimum ${OBSERVATION_TEXT_MIN_LENGTH} caractères.`)
      }
      return
    }

    if (!establishmentId || !authorMembershipId) {
      setFormError('Établissement non sélectionné.')
      return
    }

    try {
      const response = await submitMutation.mutateAsync({
        text: trimmedText,
        files: photos.map((photo) => photo.file),
      })
      clear()
      trackObservation({
        observationId: response.id,
        establishmentId,
        authorMembershipId,
        origin: 'direct_report',
        submittedAt: response.submitted_at,
      })
    } catch (error) {
      const kind = legalConsentKindFromError(error)
      if (kind) {
        setLegalKind(kind)
      }
      setFormError(resolveReportError(error))
    }
  }

  const pageShell = (content: React.ReactNode) => (
    <div className="flex flex-col gap-4 px-4 pb-4 pt-2">{content}</div>
  )

  if (!establishmentId) {
    return pageShell(
      <TerrainCard>
        <p className={cn('text-sm', terrain.muted)}>
          Sélectionnez un établissement actif pour faire remonter une observation.
        </p>
      </TerrainCard>,
    )
  }

  return (
    <div className="flex h-full min-h-0 flex-col" data-testid="report-page-root">
      <div className="min-h-0 flex-1 overflow-y-auto overscroll-y-contain px-4 pt-3">
        <div className="flex flex-col gap-5 pb-3">
          <header className="flex flex-col gap-1">
            <h1 className="text-2xl font-bold text-[#1a1a1a]">Une observation ?</h1>
            <p className={cn('text-sm', terrain.muted)}>
              Soyez précis mais ne perdez pas de temps avec la forme. La transcription et
              l’analyse envoient texte ou audio à OpenAI (
              <a
                href={PUBLIC_PRIVACY_POLICY_URL}
                className="underline"
                target="_blank"
                rel="noreferrer"
              >
                confidentialité
              </a>
              ).
            </p>
          </header>

          <ReportTextSection
            text={text}
            textLength={textLength}
            shouldReduceMotion={shouldReduceMotion ?? false}
            isRecording={isRecording}
            isTranscribing={isTranscribing}
            isSubmitPending={isSubmitPending}
            onTextChange={setText}
            onStartRecording={() => void handleStartRecording()}
            onStopRecording={handleStopRecording}
          />

          <ReportPhotosSection
            photos={photos}
            disabled={isSubmitPending}
            onPhotoSelect={handlePhotoSelect}
            onRemovePhoto={(photo) => removePhoto(photo.localId)}
          />

          {formError ? <TerrainErrorState message={formError} /> : null}
        </div>
      </div>

      <TerrainStickyFooter variant="transparent">
        <Button
          type="button"
          className={cn(
            'h-12 w-full rounded-full text-[15px] font-bold text-white',
            canSubmit
              ? cn(terrainBrandAction.bg, terrainBrandAction.hover)
              : 'bg-[#114660]/40 hover:bg-[#114660]/40',
          )}
          disabled={!canSubmit}
          onClick={() => void handleSubmit()}
        >
          {isSubmitPending ? (
            <>
              <LoaderCircle className="mr-2 h-4 w-4 animate-spin" />
              Envoi...
            </>
          ) : (
            <>
              <SendHorizonal className="mr-2 h-4 w-4" />
              Envoyer l’observation
            </>
          )}
        </Button>
      </TerrainStickyFooter>
      <LegalConsentSheet
        kind={legalKind}
        onClose={() => setLegalKind(null)}
        onAccepted={() => setFormError(null)}
      />
    </div>
  )
}
