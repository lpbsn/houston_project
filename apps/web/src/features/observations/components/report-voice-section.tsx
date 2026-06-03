import { LoaderCircle, Mic } from 'lucide-react'
import { motion } from 'framer-motion'

import { terrainTapProps } from '@/lib/terrain-motion'
import { terrain } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

const IA_HINT =
  'L’IA structure le signal et le rattache au bon périmètre opérationnel.'

type ReportVoiceSectionProps = {
  shouldReduceMotion: boolean
  isRecording: boolean
  isTranscribing: boolean
  isSubmitPending: boolean
  latestTranscript: string
  onStartRecording: () => void
  onStopRecording: () => void
}

export function ReportVoiceSection({
  shouldReduceMotion,
  isRecording,
  isTranscribing,
  isSubmitPending,
  latestTranscript,
  onStartRecording,
  onStopRecording,
}: ReportVoiceSectionProps) {
  const VoiceButton = shouldReduceMotion ? 'button' : motion.button

  const statusLabel = isTranscribing
    ? 'Transcription en cours...'
    : isRecording
      ? 'Enregistrement en cours'
      : 'Appuie pour dicter'

  return (
    <section
      aria-label="Saisie vocale"
      className="flex w-full flex-col items-center gap-2.5 py-2.5"
    >
      <p className={cn('text-center text-[13px]', terrain.textMuted)}>
        Appuie et décris le problème à voix haute
      </p>
      <VoiceButton
        type="button"
        className={cn(
          'flex h-[100px] w-[100px] items-center justify-center rounded-full border-0 p-0 text-white',
          isRecording
            ? cn(terrain.dangerBg, 'shadow-[0_0_0_12px_rgba(226,75,74,0.15),0_6px_24px_rgba(226,75,74,0.4)]')
            : cn(
                terrain.primaryBg,
                'shadow-[0_6px_24px_rgba(27,79,216,0.4)] hover:bg-[#1B4FD8]/95',
              ),
        )}
        disabled={isTranscribing || isSubmitPending}
        onClick={isRecording ? onStopRecording : onStartRecording}
        aria-label={isRecording ? 'Arrêter l’enregistrement' : 'Démarrer l’enregistrement vocal'}
        {...(!shouldReduceMotion && isRecording
          ? { animate: { scale: [1, 1.04, 1] }, transition: { repeat: Infinity, duration: 1.2 } }
          : !shouldReduceMotion && !isRecording && !isTranscribing
            ? terrainTapProps(shouldReduceMotion)
            : {})}
      >
        {isTranscribing ? (
          <LoaderCircle className="h-8 w-8 animate-spin" />
        ) : (
          <Mic className="h-8 w-8" />
        )}
      </VoiceButton>
      <p className={cn('text-center text-[10px]', terrain.textMuted)}>{statusLabel}</p>
      {latestTranscript ? (
        <div className="w-full">
          <p className={cn('mb-1 text-center text-[10px] font-semibold uppercase tracking-wide', terrain.textMuted)}>
            Dernière dictée
          </p>
          <div
            className={cn(
              'w-full rounded-xl px-3 py-3 text-center text-[13px]',
              terrain.transcript,
            )}
          >
            “{latestTranscript}”
          </div>
        </div>
      ) : null}
      <p className={cn('text-center text-[10px]', terrain.textMuted)}>{IA_HINT}</p>
    </section>
  )
}
