import { useMemo, useRef, useState } from 'react'
import { ImagePlus, LoaderCircle, Mic, Trash2 } from 'lucide-react'

import { useAuth } from '@/app/auth-provider'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
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
  formatSignalSummaryLine,
  shouldShowProcessingSignalList,
} from '@/features/observations/processing-status-popup'
import {
  MAX_OBSERVATION_PHOTOS,
  OBSERVATION_TEXT_MAX_LENGTH,
  OBSERVATION_TEXT_MIN_LENGTH,
} from '@/features/observations/types'

type PhotoDraft = {
  localId: string
  file: File
  uploadId: string | null
  status: 'uploading' | 'ready' | 'failed'
}

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
  const auth = useAuth()
  const establishmentId = auth.bootstrap?.active_membership?.establishment_id ?? null

  const [text, setText] = useState('')
  const [photos, setPhotos] = useState<PhotoDraft[]>([])
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
    return `${photos.length}/${MAX_OBSERVATION_PHOTOS} photo(s) — optionnel`
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
      setFormError(`Maximum ${MAX_OBSERVATION_PHOTOS} photos.`)
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

  const handleRemovePhoto = async (photo: PhotoDraft) => {
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

  if (!establishmentId) {
    return (
      <Card className="rounded-[1.75rem] border-[#e7dfd1] bg-[#fffaf2] p-5">
        <p className="text-sm text-[#5f574d]">
          Sélectionnez un établissement actif pour faire remonter une observation.
        </p>
      </Card>
    )
  }

  if (submittedObservationId) {
    return (
      <Card className="rounded-[1.75rem] border-[#d8ead8] bg-[#f4fbf4] p-5">
        <h2 className="text-lg font-semibold text-[#1f1a14]">Observation envoyée</h2>
        <div className="mt-2 flex items-center gap-2 text-sm text-[#5f574d]">
          {processingQuery.isLoading || processingQuery.isFetching ? (
            <LoaderCircle className="h-4 w-4 shrink-0 animate-spin" />
          ) : null}
          <p>{processingLabel}</p>
        </div>
        {processingSuccessHeadline ? (
          <p className="mt-2 text-sm font-medium text-[#1f1a14]">{processingSuccessHeadline}</p>
        ) : null}
        {showProcessingSignalList && processingSignals.length > 0 ? (
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-[#5f574d]">
            {processingSignals.map((signal) => (
              <li key={signal.id}>{formatSignalSummaryLine(signal)}</li>
            ))}
          </ul>
        ) : null}
        {processingQuery.isError ? (
          <p className="mt-2 text-sm text-[#9a3b2e]">{getErrorMessage(processingQuery.error)}</p>
        ) : null}
        <p className="mt-1 text-xs text-[#7a7268]">Référence : {submittedObservationId}</p>
        {showSignalFeedLink && onNavigate ? (
          <Button
            type="button"
            variant="outline"
            className="mt-4 h-10 w-full rounded-[1rem]"
            onClick={handleGoToSignalFeed}
          >
            Aller au feed Signal
          </Button>
        ) : null}
        <Button
          type="button"
          className="mt-3 h-10 w-full rounded-[1rem]"
          onClick={() => {
            setSubmittedObservationId(null)
          }}
        >
          Nouvelle observation
        </Button>
      </Card>
    )
  }

  return (
    <div className="flex flex-col gap-4 rounded-2xl bg-[#F5F4F0] p-4 sm:p-5">
      <h1 className="text-lg font-semibold text-[#1a1a1a]">Nouveau signal</h1>

      <Card className="space-y-3 rounded-2xl border-[#E8E6DF] bg-white p-4">
        <p className="text-xs uppercase tracking-[0.04em] text-[#7d7b75]">
          Décris à la voix puis complète si besoin
        </p>
        <div className="flex justify-center">
          <Button
            type="button"
            className="h-24 w-24 rounded-full bg-[#1B4FD8] p-0 text-white shadow-[0_6px_24px_rgba(27,79,216,0.35)] hover:bg-[#1B4FD8]/95"
            disabled={isTranscribing || submitMutation.isPending}
            onClick={isRecording ? handleStopRecording : handleStartRecording}
            aria-label={isRecording ? 'Arrêter l’enregistrement' : 'Démarrer l’enregistrement vocal'}
          >
            {isTranscribing ? (
              <LoaderCircle className="h-8 w-8 animate-spin" />
            ) : (
              <Mic className="h-8 w-8" />
            )}
          </Button>
        </div>
        <p className="text-center text-xs text-[#7d7b75]">
          {isTranscribing ? 'Transcription en cours...' : isRecording ? 'Enregistrement en cours' : 'Appuie pour dicter'}
        </p>
        {latestTranscript ? (
          <div className="rounded-xl bg-[#EEF2FF] px-3 py-2 text-center text-sm text-[#1B4FD8]">
            “{latestTranscript}”
          </div>
        ) : null}
      </Card>

      <div className="flex items-center gap-2 px-1">
        <div className="h-px flex-1 bg-[#E8E6DF]" />
        <span className="text-[11px] text-[#a3a19a]">ou décris par écrit</span>
        <div className="h-px flex-1 bg-[#E8E6DF]" />
      </div>

      <Card className="rounded-2xl border-[#E8E6DF] bg-white p-4">
        <label
          className="text-xs uppercase tracking-[0.04em] text-[#7d7b75]"
          htmlFor="observation-text"
        >
          Description
        </label>
        <textarea
          id="observation-text"
          className="mt-2 min-h-[88px] w-full resize-none rounded-[14px] border border-[#E8E6DF] bg-white px-3 py-2 text-sm text-[#1a1a1a] outline-none focus:border-[#1B4FD8]/45"
          value={text}
          onChange={(event) => setText(event.target.value.slice(0, OBSERVATION_TEXT_MAX_LENGTH))}
          placeholder="Décrivez la situation (10 à 1000 caractères)."
        />
        <p className="mt-1 text-xs text-[#7d7b75]">
          {textLength}/{OBSERVATION_TEXT_MAX_LENGTH} caractères
        </p>
      </Card>

      <Card className="rounded-2xl border-[#E8E6DF] bg-white p-4">
        <div className="flex items-center justify-between gap-2">
          <p className="text-xs uppercase tracking-[0.04em] text-[#7d7b75]">Photos</p>
          <p className="text-xs text-[#7d7b75]">{photoHint}</p>
        </div>
        <div className="mt-3">
          <label
            className="flex h-20 w-20 cursor-pointer flex-col items-center justify-center gap-1 rounded-[14px] border border-dashed border-[#E8E6DF] bg-[#F0EFE9] text-[#7d7b75] transition hover:bg-[#ebe9e2]"
            aria-disabled={photos.length >= MAX_OBSERVATION_PHOTOS || uploadMutation.isPending}
          >
            <input
              type="file"
              accept="image/jpeg,image/png,image/heic,image/heif,.heic,.heif"
              className="sr-only"
              disabled={photos.length >= MAX_OBSERVATION_PHOTOS || uploadMutation.isPending}
              onChange={handlePhotoSelect}
            />
            <ImagePlus className="h-5 w-5" />
            <span className="text-xs font-medium">Ajouter</span>
          </label>
        </div>
        <ul className="mt-3 space-y-2">
          {photos.map((photo) => (
            <li
              key={photo.localId}
              className="flex items-center justify-between rounded-[14px] border border-[#E8E6DF] bg-[#F0EFE9] px-3 py-2 text-sm"
            >
              <span className="truncate text-[#1a1a1a]">{photo.file.name}</span>
              <div className="flex items-center gap-2">
                {photo.status === 'uploading' ? (
                  <LoaderCircle className="h-4 w-4 animate-spin text-[#7d7b75]" />
                ) : null}
                {photo.status === 'failed' ? (
                  <span className="text-xs text-[#9a3b2e]">Échec</span>
                ) : null}
                <button
                  type="button"
                  className="text-[#7d7b75] hover:text-[#1a1a1a]"
                  onClick={() => void handleRemovePhoto(photo)}
                  aria-label="Supprimer la photo"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </li>
          ))}
        </ul>
      </Card>

      {formError ? (
        <p className="rounded-[14px] border border-[#f0d4cf] bg-[#fff5f3] px-3 py-2 text-sm text-[#9a3b2e]">
          {formError}
        </p>
      ) : null}

      <Button
        type="button"
        className="h-11 w-full rounded-2xl bg-[#1B4FD8] text-white hover:bg-[#1B4FD8]/95"
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
    </div>
  )
}
