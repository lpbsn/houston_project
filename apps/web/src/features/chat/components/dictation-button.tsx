import { useEffect, useRef, useState } from 'react'
import { Mic, Square } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { TerrainDialog } from '@/components/ui/terrain'
import { transcribeAudio } from '@/features/observations/api'

/** Dictation reuses Spore's consent-checked transcription endpoint. Never sends a message. */
export function DictationButton({
  establishmentId,
  disabled,
  remaining,
  onAppend,
}: {
  establishmentId: string
  disabled?: boolean
  remaining: number
  onAppend: (text: string) => void
}) {
  const [open, setOpen] = useState(false)
  const [recording, setRecording] = useState(false)
  const [busy, setBusy] = useState(false)
  const [text, setText] = useState('')
  const [error, setError] = useState<string | null>(null)
  const recorder = useRef<MediaRecorder | null>(null)
  const stream = useRef<MediaStream | null>(null)
  const timeout = useRef<ReturnType<typeof setTimeout> | null>(null)
  const generation = useRef(0)
  function release() {
    if (timeout.current) clearTimeout(timeout.current)
    timeout.current = null
    if (recorder.current && recorder.current.state !== 'inactive') recorder.current.stop()
    stream.current?.getTracks().forEach((track) => track.stop())
    stream.current = null
  }
  useEffect(
    () => () => {
      generation.current++
      release()
    },
    [establishmentId],
  )
  function close() {
    generation.current++
    release()
    setRecording(false)
    setBusy(false)
    setOpen(false)
  }
  async function start() {
    const ticket = ++generation.current
    setError(null)
    setBusy(true)
    try {
      if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined')
        throw new Error(
          'La dictée n’est pas disponible sur cet appareil. Vous pouvez écrire votre message.',
        )
      const audio = await navigator.mediaDevices.getUserMedia({ audio: true })
      if (ticket !== generation.current) {
        audio.getTracks().forEach((track) => track.stop())
        return
      }
      stream.current = audio
      const current = new MediaRecorder(audio)
      recorder.current = current
      const chunks: Blob[] = []
      current.ondataavailable = (event) => {
        if (event.data.size) chunks.push(event.data)
      }
      current.onstop = async () => {
        audio.getTracks().forEach((track) => track.stop())
        if (timeout.current) clearTimeout(timeout.current)
        if (ticket !== generation.current) return
        setRecording(false)
        setBusy(true)
        try {
          const type = current.mimeType || 'audio/webm'
          const blob = new Blob(chunks, { type })
          if (!blob.size) throw new Error('Aucun son enregistré. Réessayez.')
          const result = await transcribeAudio(
            establishmentId,
            blob,
            type.includes('mp4') ? 'dictee.m4a' : 'dictee.webm',
          )
          if (ticket === generation.current) setText(result.text)
        } catch (e) {
          if (ticket === generation.current)
            setError(e instanceof Error ? e.message : 'Transcription indisponible.')
        } finally {
          if (ticket === generation.current) setBusy(false)
        }
      }
      current.start()
      setRecording(true)
      setBusy(false)
      timeout.current = setTimeout(() => {
        if (current.state === 'recording') current.stop()
      }, 60000)
    } catch (e) {
      release()
      if (ticket === generation.current) {
        setError(e instanceof Error ? e.message : 'Microphone indisponible.')
        setBusy(false)
      }
    }
  }
  return (
    <>
      <Button
        type="button"
        variant="ghost"
        size="icon"
        aria-label="Dicter un message"
        disabled={disabled}
        onClick={() => {
          setText('')
          setError(null)
          setOpen(true)
        }}
      >
        <Mic className="h-5 w-5" />
      </Button>
      <TerrainDialog open={open} title="Dicter un message" onClose={close}>
        <div className="space-y-3 text-[#1a1a1a]">
          <p className="text-sm">
            Votre audio est envoyé au service de transcription IA de Spore. Relisez le texte avant
            de l’insérer. Aucun message n’est envoyé automatiquement. Maximum : une minute.
          </p>
          {recording ? (
            <Button onClick={() => recorder.current?.stop()}>
              <Square className="mr-2 h-4 w-4" />
              Terminer la dictée
            </Button>
          ) : (
            <Button disabled={busy} onClick={() => void start()}>
              {busy ? 'Transcription…' : 'Démarrer le microphone'}
            </Button>
          )}
          {error && <p role="alert">{error}</p>}
          <textarea
            aria-label="Transcription à relire"
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={5}
            className="w-full rounded-xl border p-3"
          />
          <p className="text-sm">
            {text.length} caractères · {Math.max(0, remaining)} disponibles dans le message.
          </p>
          <Button
            disabled={busy || recording || !text.trim() || text.length > remaining}
            onClick={() => {
              onAppend(text.trim())
              close()
            }}
          >
            Insérer dans mon message
          </Button>
        </div>
      </TerrainDialog>
    </>
  )
}
