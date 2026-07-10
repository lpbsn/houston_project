import { useEffect, useRef, useState } from 'react'
import { LoaderCircle, SendHorizonal } from 'lucide-react'
import { useReducedMotion } from 'framer-motion'

import { useAuth } from '@/app/auth-provider'
import { TerrainCard, TerrainErrorState, TerrainStickyFooter } from '@/components/ui/terrain'
import { Button } from '@/components/ui/button'
import {
  ReportPhotosSection,
  type ReportPhotoDraft,
} from '@/features/observations/components/report-photos-section'
import { ReportSuccessPanel } from '@/features/observations/components/report-success-panel'
import { ReportTextSection } from '@/features/observations/components/report-text-section'
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
import { resolveApiErrorMessage } from '@/lib/error-message'
import { terrain, terrainObservationAction } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

type ReportPageProps = {
  onNavigate?: (pathname: string) => void
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
  const photoPreviewUrlsRef = useRef<Set<string>>(new Set())

  const uploadMutation = useUploadTemporaryPhotoMutation(establishmentId)
  const deleteMutation = useDeleteTemporaryPhotoMutation(establishmentId)
  const transcribeMutation = useTranscribeAudioMutation(establishmentId)
  const submitMutation = useSubmitObservationMutation(establishmentId)

  const isSubmitPending = submitMutation.isPending

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
    !isSubmitPending &&
    !isTranscribing

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

  const resolveReportError = (error: unknown) =>
    resolveApiErrorMessage(error, ObservationsApiError, 'Une erreur est survenue.')

  function trackPreviewUrl(url: string) {
    photoPreviewUrlsRef.current.add(url)
  }

  function revokePreviewUrl(url: string) {
    if (!photoPreviewUrlsRef.current.delete(url)) {
      return
    }
    URL.revokeObjectURL(url)
  }

  function revokeAllPreviewUrls() {
    for (const url of photoPreviewUrlsRef.current) {
      URL.revokeObjectURL(url)
    }
    photoPreviewUrlsRef.current.clear()
  }

  useEffect(() => {
    return () => {
      revokeAllPreviewUrls()
    }
  }, [])

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
    const previewUrl = URL.createObjectURL(file)
    trackPreviewUrl(previewUrl)
    setPhotos((current) => [
      ...current,
      { localId, file, uploadId: null, status: 'uploading', previewUrl },
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
      setFormError(resolveReportError(error))
    }
  }

  const handleRemovePhoto = async (photo: ReportPhotoDraft) => {
    revokePreviewUrl(photo.previewUrl)
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
          setText(result.text.slice(0, OBSERVATION_TEXT_MAX_LENGTH))
        } catch (error) {
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

    const uploadIds = photos
      .map((photo) => photo.uploadId)
      .filter((id): id is string => Boolean(id))

    try {
      const response = await submitMutation.mutateAsync({
        text: trimmedText,
        temporary_upload_ids: uploadIds,
      })
      revokeAllPreviewUrls()
      setSubmittedObservationId(response.id)
      setText('')
      setPhotos([])
    } catch (error) {
      setFormError(resolveReportError(error))
    }
  }

  const handleGoToSignalFeed = () => {
    if (!onNavigate) {
      return
    }
    onNavigate('/signals')
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
          processingQuery.isError ? resolveReportError(processingQuery.error) : null
        }
        showSignalFeedLink={showSignalFeedLink}
        onGoToSignalFeed={onNavigate ? handleGoToSignalFeed : undefined}
        onNewObservation={() => setSubmittedObservationId(null)}
      />,
    )
  }

  return (
    <div className="flex min-h-full flex-col">
      <div className="flex flex-1 flex-col gap-5 px-4 pb-28 pt-3">
        <header className="flex flex-col gap-1">
          <h1 className="text-2xl font-bold text-[#1a1a1a]">Une observation ?</h1>
          <p className={cn('text-sm', terrain.muted)}>
            Soyez précis mais ne perdez pas de temps avec la forme.
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
          isUploadPending={uploadMutation.isPending}
          onPhotoSelect={(event) => void handlePhotoSelect(event)}
          onRemovePhoto={(photo) => void handleRemovePhoto(photo)}
        />

        {formError ? <TerrainErrorState message={formError} /> : null}
      </div>

      <TerrainStickyFooter variant="transparent">
        <Button
          type="button"
          className={cn(
            'h-12 w-full rounded-full text-[15px] font-bold text-white',
            canSubmit
              ? cn(terrainObservationAction.bg, terrainObservationAction.hover)
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
    </div>
  )
}
