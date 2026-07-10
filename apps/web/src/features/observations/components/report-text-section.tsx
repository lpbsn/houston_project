import { OBSERVATION_TEXT_MAX_LENGTH } from '@/features/observations/types'
import { terrain } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

import { ReportInlineMicButton } from './report-inline-mic-button'

type ReportTextSectionProps = {
  text: string
  textLength: number
  shouldReduceMotion: boolean
  isRecording: boolean
  isTranscribing: boolean
  isSubmitPending: boolean
  onTextChange: (value: string) => void
  onStartRecording: () => void
  onStopRecording: () => void
}

export function ReportTextSection({
  text,
  textLength,
  shouldReduceMotion,
  isRecording,
  isTranscribing,
  isSubmitPending,
  onTextChange,
  onStartRecording,
  onStopRecording,
}: ReportTextSectionProps) {
  return (
    <section className="flex flex-col gap-2">
      <label
        htmlFor="observation-text"
        className={cn('text-sm font-semibold', terrain.foreground)}
      >
        Décrivez l’observation
      </label>
      <div className="relative">
        <textarea
          id="observation-text"
          className={cn(
            'min-h-[150px] w-full resize-none rounded-[24px] border border-[#E8E6DF] bg-white',
            'px-4 pb-12 pt-3 pr-14 text-base leading-relaxed outline-none',
            terrain.foreground,
            'placeholder:text-[#aaa]',
          )}
          value={text}
          onChange={(event) =>
            onTextChange(event.target.value.slice(0, OBSERVATION_TEXT_MAX_LENGTH))
          }
          placeholder="Détaillez ce que vous voyez..."
        />
        <div className="absolute bottom-3 left-4">
          <p className={cn('text-xs', terrain.muted)}>
            {textLength}/{OBSERVATION_TEXT_MAX_LENGTH}
          </p>
        </div>
        <div className="absolute bottom-3 right-3">
          <ReportInlineMicButton
            shouldReduceMotion={shouldReduceMotion}
            isRecording={isRecording}
            isTranscribing={isTranscribing}
            isSubmitPending={isSubmitPending}
            onStartRecording={onStartRecording}
            onStopRecording={onStopRecording}
          />
        </div>
      </div>
    </section>
  )
}
