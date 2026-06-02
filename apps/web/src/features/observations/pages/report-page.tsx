import { useMemo, useRef, useState } from 'react'
import { LoaderCircle, Mic, Trash2 } from 'lucide-react'

import { useAuth } from '@/app/auth-provider'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { ObservationsApiError } from '@/features/observations/api'
import {
  useDeleteTemporaryPhotoMutation,
  useSubmitObservationMutation,
  useTranscribeAudioMutation,
  useUploadTemporaryPhotoMutation,
} from '@/features/observations/hooks'
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

function getErrorMessage(error: unknown): string {
  if (error instanceof ObservationsApiError) {
    return error.detail
  }
  if (error instanceof Error) {
    return error.message
  }
  return 'Une erreur est survenue.'
}

export function ReportPage() {
  const auth = useAuth()
  const establishmentId = auth.bootstrap?.active_membership?.establishment_id ?? null

  const [text, setText] = useState('')
  const [photos, setPhotos] = useState<PhotoDraft[]>([])
  const [formError, setFormError] = useState<string | null>(null)
  const [isRecording, setIsRecording] = useState(false)
  const [isTranscribing, setIsTranscribing] = useState(false)
  const [submittedObservationId, setSubmittedObservationId] = useState<string | null>(null)
  const [processingStatus, setProcessingStatus] = useState<string | null>(null)

  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])

  const uploadMutation = useUploadTemporaryPhotoMutation(establishmentId)
  const deleteMutation = useDeleteTemporaryPhotoMutation(establishmentId)
  const transcribeMutation = useTranscribeAudioMutation(establishmentId)
  const submitMutation = useSubmitObservationMutation(establishmentId)

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
      setProcessingStatus(response.processing_status)
      setText('')
      setPhotos([])
    } catch (error) {
      setFormError(getErrorMessage(error))
    }
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
        <p className="mt-2 text-sm text-[#5f574d]">
          Votre signalement a bien été enregistré. L&apos;analyse est en cours
          {processingStatus ? ` (${processingStatus})` : ''}.
        </p>
        <p className="mt-1 text-xs text-[#7a7268]">Référence : {submittedObservationId}</p>
        <Button
          type="button"
          className="mt-4 h-10 w-full rounded-[1rem]"
          onClick={() => {
            setSubmittedObservationId(null)
            setProcessingStatus(null)
          }}
        >
          Nouvelle observation
        </Button>
      </Card>
    )
  }

  return (
    <div className="flex flex-col gap-4">
      <Card className="rounded-[1.75rem] border-[#e7dfd1] bg-[#fffaf2] p-5">
        <label className="text-sm font-medium text-[#1f1a14]" htmlFor="observation-text">
          Description
        </label>
        <textarea
          id="observation-text"
          className="mt-2 min-h-36 w-full rounded-[1rem] border border-[#e7dfd1] bg-white px-3 py-2 text-sm text-[#1f1a14] outline-none focus:border-[#c9b89a]"
          value={text}
          onChange={(event) => setText(event.target.value.slice(0, OBSERVATION_TEXT_MAX_LENGTH))}
          placeholder="Décrivez la situation (10 à 1000 caractères)."
        />
        <p className="mt-1 text-xs text-[#7a7268]">
          {textLength}/{OBSERVATION_TEXT_MAX_LENGTH} caractères
        </p>
      </Card>

      <Card className="rounded-[1.75rem] border-[#e7dfd1] bg-[#fffaf2] p-5">
        <div className="flex items-center justify-between gap-2">
          <p className="text-sm font-medium text-[#1f1a14]">Audio</p>
          <p className="text-xs text-[#7a7268]">Non conservé après transcription</p>
        </div>
        <div className="mt-3 flex flex-col gap-2 sm:flex-row">
          <Button
            type="button"
            variant="outline"
            className="h-10 flex-1 rounded-[1rem] border-[#e7dfd1]"
            disabled={isTranscribing || submitMutation.isPending}
            onClick={isRecording ? handleStopRecording : handleStartRecording}
          >
            {isTranscribing ? (
              <>
                <LoaderCircle className="mr-2 h-4 w-4 animate-spin" />
                Transcription...
              </>
            ) : isRecording ? (
              'Arrêter'
            ) : (
              <>
                <Mic className="mr-2 h-4 w-4" />
                Dicter
              </>
            )}
          </Button>
        </div>
      </Card>

      <Card className="rounded-[1.75rem] border-[#e7dfd1] bg-[#fffaf2] p-5">
        <div className="flex items-center justify-between gap-2">
          <p className="text-sm font-medium text-[#1f1a14]">Photos</p>
          <p className="text-xs text-[#7a7268]">{photoHint}</p>
        </div>
        <input
          type="file"
          accept="image/jpeg,image/png,image/heic,image/heif,.heic,.heif"
          className="mt-3 block w-full text-sm text-[#5f574d]"
          disabled={photos.length >= MAX_OBSERVATION_PHOTOS || uploadMutation.isPending}
          onChange={handlePhotoSelect}
        />
        <ul className="mt-3 space-y-2">
          {photos.map((photo) => (
            <li
              key={photo.localId}
              className="flex items-center justify-between rounded-[1rem] border border-[#efe6d7] bg-white px-3 py-2 text-sm"
            >
              <span className="truncate text-[#1f1a14]">{photo.file.name}</span>
              <div className="flex items-center gap-2">
                {photo.status === 'uploading' ? (
                  <LoaderCircle className="h-4 w-4 animate-spin text-[#7a7268]" />
                ) : null}
                {photo.status === 'failed' ? (
                  <span className="text-xs text-[#9a3b2e]">Échec</span>
                ) : null}
                <button
                  type="button"
                  className="text-[#7a7268] hover:text-[#1f1a14]"
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
        <p className="rounded-[1rem] border border-[#f0d4cf] bg-[#fff5f3] px-3 py-2 text-sm text-[#9a3b2e]">
          {formError}
        </p>
      ) : null}

      <Button
        type="button"
        className="h-11 w-full rounded-[1rem]"
        disabled={!canSubmit}
        onClick={() => void handleSubmit()}
      >
        {submitMutation.isPending ? (
          <>
            <LoaderCircle className="mr-2 h-4 w-4 animate-spin" />
            Envoi...
          </>
        ) : (
          'Envoyer l’observation'
        )}
      </Button>
    </div>
  )
}
