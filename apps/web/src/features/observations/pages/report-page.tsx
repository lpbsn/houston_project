import { useMemo, useRef, useState } from 'react'
import { LoaderCircle } from 'lucide-react'
import { useReducedMotion } from 'framer-motion'

import { useAuth } from '@/app/auth-provider'
import {
  TerrainCard,
  TerrainErrorState,
  TerrainFieldLabel,
  TerrainOrDivider,
} from '@/components/ui/terrain'
import { Button } from '@/components/ui/button'
import { ReportPhotosSection, type ReportPhotoDraft } from '@/features/observations/components/report-photos-section'
import { ReportSuccessPanel } from '@/features/observations/components/report-success-panel'
import { ReportVoiceSection } from '@/features/observations/components/report-voice-section'
import { ObservationsApiError } from '@/features/observations/api'
import {
  useDeleteTemporaryPhotoMutation,
  useObservationProcessingStatusQuery,
  useSubmitObservationMutation,
  useTranscribeAudioMutation,
  useUploadTemporaryPhotoMutation,
} from '@/features/observations/hooks'
import {
  getProcessingUxLabel,
  shouldShowSignalFeedNavigation,
} from '@/features/observations/processing-status-labels'
import {
  formatProcessingSuccessHeadline,
  shouldShowProcessingSignalList,
} from '@/features/observations/processing-status-popup'
import {
  MAX_OBSERVATION_PHOTOS,
  OBSERVATION_TEXT_MAX_LENGTH,
  OBSERVATION_TEXT_MIN_LENGTH,
} from '@/features/observations/types'
import { terrain } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

type ReportPageProps = {
  onNavigate?: (pathname: string) => void
}

function getErrorMessage(error: unknown): string {
  if (error instanceof ObservationsApiError) {
    return error.detail
  }
  if (error instanceof Error) {
    return error.message
  }
  return 'Une erreur est survenue.'
}

export function ReportPage({ onNavigate }: ReportPageProps) {
  const shouldReduceMotion = useReducedMotion()
  const auth = useAuth()
  const establishmentId = auth.bootstrap?.active_membership?.establishment_id ?? null

  const [text, setText] = useState('')
  const [photos, setPhotos] = useState<ReportPhotoDraft[]>([])
  const [formError, setFormError] = useState<string | null>(null)
  const [isRecording, setIsRecording] = useState(false)
  const [isTranscribing, setIsTranscribing] = useState(false)
  const [submittedObservationId, setSubmittedObservationId] = useState<string | null>(null)

  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])

  const uploadMutation = useUploadTemporaryPhotoMutation(establishmentId)
  const deleteMutation = useDeleteTemporaryPhotoMutation(establishmentId)
  const transcribeMutation = useTranscribeAudioMutation(establishmentId)
  const submitMutation = useSubmitObservationMutation(establishmentId)

  const processingQuery = useObservationProcessingStatusQuery(
    establishmentId,
    submittedObservationId,
    { enabled: Boolean(submittedObservationId) },
  )

  const trimmedText = text.trim()
  const textLength = trimmedText.length
  const canSubmit =
    textLength >= OBSERVATION_TEXT_MIN_LENGTH &&
    textLength <= OBSERVATION_TEXT_MAX_LENGTH &&
    photos.every((photo) => photo.status === 'ready') &&
    !uploadMutation.isPending &&
    !submitMutation.isPending &&
    !isTranscribing

  const photoHint = useMemo(() => {
    return `${photos.length}/${MAX_OBSERVATION_PHOTOS} photos — optionnel`
  }, [photos.length])
  const latestTranscript = transcribeMutation.data?.text?.trim() ?? ''

  const processingLabel = processingQuery.data?.ux_status
    ? getProcessingUxLabel(processingQuery.data.ux_status)
    : getProcessingUxLabel('analysis_queued')

  const showSignalFeedLink =
    processingQuery.data?.ux_status != null &&
    shouldShowSignalFeedNavigation(processingQuery.data.ux_status)

  const processingSignals = processingQuery.data?.signals ?? []

  const processingSuccessHeadline = processingQuery.data?.ux_status
    ? formatProcessingSuccessHeadline(
        processingSignals.length,
        processingQuery.data.ux_status,
      )
    : null

  const showProcessingSignalList = shouldShowProcessingSignalList(
    processingQuery.data?.ux_status,
  )

  const handlePhotoSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file || !establishmentId) {
      return
    }
    if (photos.length >= MAX_OBSERVATION_PHOTOS) {
      setFormError(`Limite : ${MAX_OBSERVATION_PHOTOS} photos maximum.`)
      return
    }

    const localId = crypto.randomUUID()
    setPhotos((current) => [
      ...current,
      { localId, file, uploadId: null, status: 'uploading' },
    ])
    setFormError(null)

    try {
      const upload = await uploadMutation.mutateAsync(file)
      setPhotos((current) =>
        current.map((photo) =>
          photo.localId === localId
            ? { ...photo, uploadId: upload.id, status: 'ready' }
            : photo,
        ),
      )
    } catch (error) {
      setPhotos((current) =>
        current.map((photo) =>
          photo.localId === localId ? { ...photo, status: 'failed' } : photo,
        ),
      )
      setFormError(getErrorMessage(error))
    }
  }

  const handleRemovePhoto = async (photo: ReportPhotoDraft) => {
    setPhotos((current) => current.filter((item) => item.localId !== photo.localId))
    if (photo.uploadId && establishmentId) {
      try {
        await deleteMutation.mutateAsync(photo.uploadId)
      } catch {
        // Best-effort cleanup; draft already removed locally.
      }
    }
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
          setText((current) => {
            const merged = current.trim() ? `${current.trim()}\n${result.text}` : result.text
            return merged.slice(0, OBSERVATION_TEXT_MAX_LENGTH)
          })
        } catch (error) {
          setFormError(getErrorMessage(error))
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

    try {
      const response = await submitMutation.mutateAsync({
        text: trimmedText,
        temporary_upload_ids: photos
          .map((photo) => photo.uploadId)
          .filter((id): id is string => Boolean(id)),
      })
      setSubmittedObservationId(response.id)
      setText('')
      setPhotos([])
    } catch (error) {
      setFormError(getErrorMessage(error))
    }
  }

  const handleGoToSignalFeed = () => {
    if (!onNavigate) {
      return
    }
    onNavigate('/signals')
  }

  const pageShell = (content: React.ReactNode) => (
    <div className="flex flex-col gap-4 px-3 pb-4 pt-2">{content}</div>
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

  if (submittedObservationId) {
    return pageShell(
      <ReportSuccessPanel
        observationId={submittedObservationId}
        processingLabel={processingLabel}
        processingSuccessHeadline={processingSuccessHeadline}
        showProcessingSignalList={showProcessingSignalList}
        processingSignals={processingSignals}
        isProcessingLoading={processingQuery.isLoading || processingQuery.isFetching}
        processingErrorMessage={
          processingQuery.isError ? getErrorMessage(processingQuery.error) : null
        }
        showSignalFeedLink={showSignalFeedLink}
        onGoToSignalFeed={onNavigate ? handleGoToSignalFeed : undefined}
        onNewObservation={() => setSubmittedObservationId(null)}
      />,
    )
  }

  return pageShell(
    <>
      <ReportVoiceSection
        shouldReduceMotion={shouldReduceMotion}
        isRecording={isRecording}
        isTranscribing={isTranscribing}
        isSubmitPending={submitMutation.isPending}
        latestTranscript={latestTranscript}
        onStartRecording={() => void handleStartRecording()}
        onStopRecording={handleStopRecording}
      />

      <TerrainOrDivider />

      <TerrainCard>
        <TerrainFieldLabel htmlFor="observation-text">Description</TerrainFieldLabel>
        <textarea
          id="observation-text"
          className={cn(
            'mt-2 min-h-[72px] w-full resize-none border-0 bg-transparent p-0 text-[13px] leading-relaxed outline-none',
            terrain.foreground,
            'placeholder:text-[#aaa]',
          )}
          value={text}
          onChange={(event) => setText(event.target.value.slice(0, OBSERVATION_TEXT_MAX_LENGTH))}
          placeholder="Décrivez le problème observé..."
        />
        <p className={cn('mt-1 text-xs', terrain.muted)}>
          {textLength}/{OBSERVATION_TEXT_MAX_LENGTH} caractères (min. {OBSERVATION_TEXT_MIN_LENGTH})
        </p>
      </TerrainCard>

      <ReportPhotosSection
        photos={photos}
        photoHint={photoHint}
        isUploadPending={uploadMutation.isPending}
        onPhotoSelect={(event) => void handlePhotoSelect(event)}
        onRemovePhoto={(photo) => void handleRemovePhoto(photo)}
      />

      {formError ? <TerrainErrorState message={formError} /> : null}

      <Button
        type="button"
        className={cn(
          'h-12 w-full rounded-2xl text-[15px] font-bold text-white hover:bg-[#1B4FD8]/95',
          terrain.primaryBg,
        )}
        disabled={!canSubmit}
        onClick={() => void handleSubmit()}
      >
        {submitMutation.isPending ? (
          <>
            <LoaderCircle className="mr-2 h-4 w-4 animate-spin" />
            Envoi...
          </>
        ) : (
          'Envoyer le signal'
        )}
      </Button>
    </>,
  )
}
