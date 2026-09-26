import { LoaderCircle, Mic, Square } from 'lucide-react'
import { motion } from 'framer-motion'

import { terrainTapProps } from '@/lib/terrain-motion'
import { terrain, terrainBrandAction, terrainInProgress } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

type ReportInlineMicButtonProps = {
  shouldReduceMotion: boolean
  isRecording: boolean
  isTranscribing: boolean
  isSubmitPending: boolean
  onStartRecording: () => void
  onStopRecording: () => void
}

export function ReportInlineMicButton({
  shouldReduceMotion,
  isRecording,
  isTranscribing,
  isSubmitPending,
  onStartRecording,
  onStopRecording,
}: ReportInlineMicButtonProps) {
  const VoiceButton = shouldReduceMotion ? 'button' : motion.button
  const disabled = isTranscribing || isSubmitPending

  const idleClass = cn(
    terrainBrandAction.bg,
    terrainBrandAction.hover,
    'shadow-[0_2px_8px_rgba(17,70,96,0.28)] ring-2 ring-white/90',
  )
  const recordingClass = cn(
    terrain.dangerBg,
    'shadow-[0_0_0_6px_rgba(226,75,74,0.18),0_4px_14px_rgba(226,75,74,0.35)]',
  )
  const processingClass = cn(
    terrainInProgress.badgeSolid,
    'shadow-[0_2px_10px_rgba(58,122,150,0.35)] ring-2 ring-[#E8F2F5]',
  )

  let motionProps = {}
  if (!shouldReduceMotion) {
    if (isRecording) {
      motionProps = {
        animate: {
          scale: [1, 1.06, 1],
          boxShadow: [
            '0 0 0 6px rgba(226,75,74,0.18), 0 4px 14px rgba(226,75,74,0.35)',
            '0 0 0 10px rgba(226,75,74,0.08), 0 4px 18px rgba(226,75,74,0.4)',
            '0 0 0 6px rgba(226,75,74,0.18), 0 4px 14px rgba(226,75,74,0.35)',
          ],
        },
        transition: { repeat: Infinity, duration: 1.1, ease: 'easeInOut' },
      }
    } else if (isTranscribing) {
      motionProps = {
        animate: { opacity: [1, 0.72, 1] },
        transition: { repeat: Infinity, duration: 1.4, ease: 'easeInOut' },
      }
    } else if (!disabled) {
      motionProps = terrainTapProps(shouldReduceMotion)
    }
  }

  return (
    <VoiceButton
      type="button"
      data-mic-state={isRecording ? 'recording' : isTranscribing ? 'processing' : 'idle'}
      className={cn(
        'flex h-12 w-12 min-h-12 min-w-12 items-center justify-center rounded-full border-0 p-0 text-white',
        isRecording ? recordingClass : isTranscribing ? processingClass : idleClass,
      )}
      disabled={disabled}
      onClick={isRecording ? onStopRecording : onStartRecording}
      aria-label={
        isRecording
          ? 'Arrêter l’enregistrement'
          : isTranscribing
            ? 'Transcription en cours'
            : 'Démarrer l’enregistrement vocal'
      }
      {...motionProps}
    >
      {isTranscribing ? (
        <LoaderCircle
          className={cn('h-5 w-5', !shouldReduceMotion && 'animate-spin')}
          aria-hidden
        />
      ) : isRecording ? (
        <Square className="h-4 w-4 fill-current" aria-hidden />
      ) : (
        <Mic className="h-5 w-5" aria-hidden />
      )}
    </VoiceButton>
  )
}
