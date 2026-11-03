import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { LoaderCircle, Mic, Square } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { ObservationsApiError, transcribeAudio } from '@/features/observations/api'
import { isAiConsentRequired } from '@/lib/legal'
import { isNetworkFailure, NETWORK_FAILURE_MESSAGE } from '@/lib/network-error'
import { actionPlanFeedTealTextClassName, terrain } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

const RECORDING_LIMIT_MS = 60_000

export type DictationPhase = 'idle' | 'recording' | 'transcribing'

export type DictationActivity = {
  phase: DictationPhase
  error: string | null
}

export const IDLE_DICTATION: DictationActivity = { phase: 'idle', error: null }

/** Dictation reuses Spore's consent-checked transcription endpoint. Never sends a message. */
export function DictationButton({
  establishmentId,
  disabled,
  onAppend,
  onActivityChange,
  className,
}: {
  establishmentId: string
  disabled?: boolean
  onAppend: (text: string) => string | null
  onActivityChange?: (activity: DictationActivity) => void
  className?: string
}) {
  const [activity, setActivity] = useState<DictationActivity>(IDLE_DICTATION)
  const recorder = useRef<MediaRecorder | null>(null)
  const stream = useRef<MediaStream | null>(null)
  const chunks = useRef<Blob[]>([])
  const timeout = useRef<ReturnType<typeof setTimeout> | null>(null)
  const generation = useRef(0)
  const starting = useRef(false)
  const phaseRef = useRef<DictationPhase>(IDLE_DICTATION.phase)
  const onAppendRef = useRef(onAppend)
  const onActivityChangeRef = useRef(onActivityChange)
  useLayoutEffect(() => {
    onAppendRef.current = onAppend
    onActivityChangeRef.current = onActivityChange
  }, [onAppend, onActivityChange])

  function publish(next: DictationActivity) {
    phaseRef.current = next.phase
    setActivity(next)
    onActivityChangeRef.current?.(next)
  }

  function release() {
    if (timeout.current) clearTimeout(timeout.current)
    timeout.current = null
    const current = recorder.current
    recorder.current = null
    if (current && current.state !== 'inactive') {
      current.ondataavailable = null
      current.onstop = null
      current.stop()
    }
    stream.current?.getTracks().forEach((track) => track.stop())
    stream.current = null
    chunks.current = []
  }

  useEffect(
    () => () => {
      generation.current += 1
      release()
      onActivityChangeRef.current?.(IDLE_DICTATION)
    },
    [establishmentId],
  )

  async function finish(blob: Blob, type: string, ticket: number) {
    try {
      const result = await transcribeAudio(
        establishmentId,
        blob,
        type.includes('mp4') ? 'dictee.m4a' : 'dictee.webm',
      )
      if (ticket !== generation.current) return
      if (!result.text.trim()) {
        publish({ phase: 'idle', error: 'La transcription est vide. Réessayez.' })
        return
      }
      const rejection = onAppendRef.current(result.text)
      if (ticket !== generation.current) return
      publish({ phase: 'idle', error: rejection })
    } catch (error) {
      if (ticket !== generation.current) return
      publish({ phase: 'idle', error: transcriptionFailureMessage(error) })
    }
  }

  async function start() {
    if (disabled || phaseRef.current !== 'idle' || starting.current) return
    const ticket = ++generation.current
    starting.current = true
    publish({ phase: 'recording', error: null })
    try {
      if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
        throw new Error(
          'La dictée n’est pas disponible sur cet appareil. Vous pouvez écrire votre message.',
        )
      }
      const audio = await navigator.mediaDevices.getUserMedia({ audio: true })
      if (ticket !== generation.current) {
        audio.getTracks().forEach((track) => track.stop())
        return
      }
      stream.current = audio
      const current = new MediaRecorder(audio)
      recorder.current = current
      chunks.current = []
      current.ondataavailable = (event) => {
        if (event.data.size) chunks.current.push(event.data)
      }
      current.onstop = () => {
        const type = current.mimeType || 'audio/webm'
        const recorded = chunks.current.splice(0, chunks.current.length)
        stream.current?.getTracks().forEach((track) => track.stop())
        stream.current = null
        recorder.current = null
        if (timeout.current) clearTimeout(timeout.current)
        timeout.current = null
        if (ticket !== generation.current) return
        const blob = new Blob(recorded, { type })
        if (!blob.size) {
          publish({ phase: 'idle', error: 'Aucun son enregistré. Réessayez.' })
          return
        }
        publish({ phase: 'transcribing', error: null })
        void finish(blob, type, ticket)
      }
      current.start()
      timeout.current = setTimeout(() => {
        if (current.state === 'recording') current.stop()
      }, RECORDING_LIMIT_MS)
    } catch (error) {
      release()
      if (ticket === generation.current) {
        publish({
          phase: 'idle',
          error:
            error instanceof Error &&
            error.message.startsWith('La dictée n’est pas disponible')
              ? error.message
              : 'Microphone indisponible. Vous pouvez écrire votre message.',
        })
      }
    } finally {
      starting.current = false
    }
  }

  function stop() {
    const current = recorder.current
    if (current && current.state === 'recording') {
      current.stop()
      return
    }
    // A second press while stop is already flushing must not cancel the transcription.
    if (current || phaseRef.current === 'transcribing') return
    if (phaseRef.current !== 'recording') return
    generation.current += 1
    release()
    publish(IDLE_DICTATION)
  }

  const recording = activity.phase === 'recording'
  const transcribing = activity.phase === 'transcribing'
  return (
    <Button
      type="button"
      variant="ghost"
      size="icon"
      className={cn(
        className,
        recording && 'bg-[#FDECEC] text-[#E24B4A] hover:bg-[#FDECEC] hover:text-[#E24B4A]',
        transcribing && cn(actionPlanFeedTealTextClassName, 'disabled:opacity-100'),
      )}
      data-mic-state={recording ? 'recording' : transcribing ? 'processing' : 'idle'}
      aria-pressed={recording}
      aria-label={
        recording
          ? 'Arrêter l’enregistrement'
          : transcribing
            ? 'Transcription en cours'
            : 'Dicter un message'
      }
      disabled={transcribing || (disabled && !recording)}
      onClick={() => {
        if (phaseRef.current === 'recording') stop()
        else void start()
      }}
    >
      {transcribing ? (
        <LoaderCircle className="h-5 w-5 animate-spin" aria-hidden />
      ) : recording ? (
        <Square className={cn('h-4 w-4 fill-current', terrain.danger)} aria-hidden />
      ) : (
        <Mic className="h-5 w-5" aria-hidden />
      )}
    </Button>
  )
}

export function DictationNotice({ activity }: { activity: DictationActivity }) {
  if (activity.phase === 'transcribing') {
    return (
      <span role="status" className={cn('text-xs font-medium', actionPlanFeedTealTextClassName)}>
        Transcription en cours…
      </span>
    )
  }
  if (activity.error) {
    return (
      <span role="alert" className={cn('text-xs', terrain.danger)}>
        {activity.error}
      </span>
    )
  }
  return null
}

function transcriptionFailureMessage(error: unknown): string {
  if (isNetworkFailure(error)) return NETWORK_FAILURE_MESSAGE
  if (error instanceof ObservationsApiError && isAiConsentRequired(error)) {
    return 'Activez le traitement OpenAI dans Général pour utiliser la dictée.'
  }
  if (error instanceof ObservationsApiError && error.code === 'transcription_timeout') {
    return 'La transcription a pris trop de temps. Réessayez.'
  }
  return 'La transcription a échoué. Réessayez ou écrivez votre message.'
}
