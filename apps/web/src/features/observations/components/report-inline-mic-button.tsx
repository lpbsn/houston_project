import { LoaderCircle, Mic } from 'lucide-react'
import { motion } from 'framer-motion'

import { terrainTapProps } from '@/lib/terrain-motion'
import { terrain, terrainBrandAction } from '@/lib/terrain-styles'
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

  return (
    <VoiceButton
      type="button"
      className={cn(
        'flex h-11 w-11 items-center justify-center rounded-full border-0 p-0 text-white',
        isRecording
          ? cn(
              terrain.dangerBg,
              'shadow-[0_0_0_8px_rgba(226,75,74,0.15),0_4px_16px_rgba(226,75,74,0.35)]',
            )
          : cn(terrainBrandAction.bg, terrainBrandAction.hover),
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
        <LoaderCircle className="h-5 w-5 animate-spin" />
      ) : (
        <Mic className="h-5 w-5" />
      )}
    </VoiceButton>
  )
}
