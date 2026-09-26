import { useEffect, useRef, useState } from 'react'
import { LoaderCircle, SendHorizonal } from 'lucide-react'
import { useReducedMotion } from 'framer-motion'

import { useAuth } from '@/app/auth-provider'
import { useTerrainShellLayout } from '@/components/layout/terrain-shell-layout'
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
import { appendObservationTranscription } from '@/features/observations/lib/append-observation-transcription'
import { getReportingComposeDraft } from '@/features/observations/lib/observation-compose-draft-store'
import { useReportingComposeDraft } from '@/features/observations/lib/use-observation-compose-draft'
import {
  MAX_OBSERVATION_PHOTOS,
  OBSERVATION_TEXT_MAX_LENGTH,
  OBSERVATION_TEXT_MIN_LENGTH,
} from '@/features/observations/types'
import { resyncBootstrapAfterLegalError } from '@/features/auth/api'
import { isDesktopWebLanding } from '@/features/auth/lib/authenticated-landing'
import { resolveApiErrorMessage } from '@/lib/error-message'
import { useNativeKeyboardOpen } from '@/lib/native-keyboard'
import {
  OBSERVATION_REQUIRES_AI_CONSENT_MESSAGE,
  PUBLIC_PRIVACY_POLICY_URL,
  readAiConsentStatus,
} from '@/lib/legal'
import { useLgViewport } from '@/lib/lg-viewport'
import { useNetworkStatus } from '@/lib/network-status'
import { terrain, terrainBrandAction } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

export function ReportPage({ establishmentId: establishmentIdProp }: { establishmentId?: string | null } = {}) {
  const shouldReduceMotion = useReducedMotion()
  const isDesktopWeb = isDesktopWebLanding(useLgViewport())
  const composeLayout = isDesktopWeb ? 'desktop' : 'field'
  const isNativeKeyboardOpen = useNativeKeyboardOpen()
  const { showBottomNav } = useTerrainShellLayout()
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
  const [isRecording, setIsRecording] = useState(false)
  const aiConsentGranted = readAiConsentStatus(auth.user ?? auth.bootstrap?.user) === 'granted'
  const [isTranscribing, setIsTranscribing] = useState(false)

  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const mountedRef = useRef(true)
  const activeEstablishmentIdRef = useRef(establishmentId)

  useEffect(() => {
    mountedRef.current = true
    activeEstablishmentIdRef.current = establishmentId
    return () => {
      mountedRef.current = false
    }
  }, [establishmentId])

  const transcribeMutation = useTranscribeAudioMutation(establishmentId)
  const submitMutation = useSubmitObservationComposeMutation(establishmentId)

  const isSubmitPending = submitMutation.isPending

  const trimmedText = text.trim()
  const textLength = trimmedText.length
  const canSubmit =
    aiConsentGranted &&
    textLength >= OBSERVATION_TEXT_MIN_LENGTH &&
    textLength <= OBSERVATION_TEXT_MAX_LENGTH &&
    isOnline &&
    !isSubmitPending &&
    !isTranscribing

  const horizontalSafePad = !isDesktopWeb
    ? 'pl-[max(1rem,var(--app-safe-left))] pr-[max(1rem,var(--app-safe-right))]'
    : 'px-4'

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
    if (!establishmentId) {
      return
    }
    const recordingEstablishmentId = establishmentId
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
          if (
            mountedRef.current &&
            activeEstablishmentIdRef.current === recordingEstablishmentId
          ) {
            setFormError('Enregistrement audio trop court.')
          }
          return
        }
        if (
          mountedRef.current &&
          activeEstablishmentIdRef.current === recordingEstablishmentId
        ) {
          setIsTranscribing(true)
        }
        try {
          const result = await transcribeMutation.mutateAsync({
            blob,
            fileName: 'observation-audio.webm',
          })
          const stillActive =
            mountedRef.current &&
            activeEstablishmentIdRef.current === recordingEstablishmentId
          if (!stillActive) {
            return
          }
          const currentText = getReportingComposeDraft(recordingEstablishmentId).text
          setText(
            appendObservationTranscription(
              currentText,
              result.text,
              OBSERVATION_TEXT_MAX_LENGTH,
            ),
          )
        } catch (error) {
          const stillActive =
            mountedRef.current &&
            activeEstablishmentIdRef.current === recordingEstablishmentId
          if (!stillActive) {
            return
          }
          const bootstrap = await resyncBootstrapAfterLegalError(error)
          if (
            !mountedRef.current ||
            activeEstablishmentIdRef.current !== recordingEstablishmentId
          ) {
            return
          }
          setFormError(
            readAiConsentStatus(bootstrap?.user ?? auth.user ?? auth.bootstrap?.user) ===
              'declined'
              ? OBSERVATION_REQUIRES_AI_CONSENT_MESSAGE
              : resolveReportError(error),
          )
        } finally {
          if (
            mountedRef.current &&
            activeEstablishmentIdRef.current === recordingEstablishmentId
          ) {
            setIsTranscribing(false)
          }
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

    if (!aiConsentGranted) {
      setFormError(OBSERVATION_REQUIRES_AI_CONSENT_MESSAGE)
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
      const bootstrap = await resyncBootstrapAfterLegalError(error)
      setFormError(
        readAiConsentStatus(bootstrap?.user ?? auth.user ?? auth.bootstrap?.user) === 'declined'
          ? OBSERVATION_REQUIRES_AI_CONSENT_MESSAGE
          : resolveReportError(error),
      )
    }
  }

  const submitButton = (
    <Button
      type="button"
      className={cn(
        'text-[15px] font-bold text-white',
        isDesktopWeb ? 'h-10 w-auto rounded-lg px-4' : 'h-12 w-full rounded-xl',
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
  )

  const pageShell = (content: React.ReactNode) => (
    <div className={cn('flex flex-col gap-4 pb-4 pt-2', horizontalSafePad)}>{content}</div>
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
    <div
      className={cn(
        'flex h-full min-h-0 flex-col',
        isDesktopWeb && 'mx-auto w-full max-w-2xl',
      )}
      data-testid="report-page-root"
    >
      <div
        className={cn(
          'min-h-0 flex-1 overflow-y-auto overscroll-y-contain pt-3',
          horizontalSafePad,
        )}
      >
        <div className="flex flex-col gap-5 pb-3">
          <header className="flex flex-col gap-1">
            <p className={cn('text-xs', terrain.muted)}>
              Texte ou vocal · traitement OpenAI (
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
            layout={composeLayout}
            shouldReduceMotion={shouldReduceMotion ?? false}
            isRecording={isRecording}
            isTranscribing={isTranscribing}
            isSubmitPending={isSubmitPending}
            onTextChange={setText}
            onStartRecording={
              aiConsentGranted
                ? () => void handleStartRecording()
                : () => {
                    setFormError(OBSERVATION_REQUIRES_AI_CONSENT_MESSAGE)
                  }
            }
            onStopRecording={handleStopRecording}
          />

          <ReportPhotosSection
            photos={photos}
            layout={composeLayout}
            disabled={isSubmitPending}
            onPhotoSelect={handlePhotoSelect}
            onRemovePhoto={(photo) => removePhoto(photo.localId)}
          />

          {isDesktopWeb ? <div className="flex justify-end pt-1">{submitButton}</div> : null}

          {!aiConsentGranted ? (
            <TerrainErrorState message={OBSERVATION_REQUIRES_AI_CONSENT_MESSAGE} />
          ) : null}
          {formError ? <TerrainErrorState message={formError} /> : null}
        </div>
      </div>

      {!isDesktopWeb && !isNativeKeyboardOpen ? (
        <TerrainStickyFooter
          variant="transparent"
          className={cn(
            'px-0 pl-[max(1rem,var(--app-safe-left))] pr-[max(1rem,var(--app-safe-right))]',
            showBottomNav && 'pb-3',
          )}
        >
          {submitButton}
        </TerrainStickyFooter>
      ) : null}
    </div>
  )
}
