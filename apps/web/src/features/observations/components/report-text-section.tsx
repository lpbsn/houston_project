import { OBSERVATION_TEXT_MAX_LENGTH, type ReportComposeLayout } from '@/features/observations/types'
import { actionPlanFeedTealTextClassName, terrain } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

import { ReportInlineMicButton } from './report-inline-mic-button'

type ReportTextSectionProps = {
  text: string
  textLength: number
  layout?: ReportComposeLayout
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
  layout = 'desktop',
  shouldReduceMotion,
  isRecording,
  isTranscribing,
  isSubmitPending,
  onTextChange,
  onStartRecording,
  onStopRecording,
}: ReportTextSectionProps) {
  const isField = layout === 'field'
  const voiceStatus =
    isField && isRecording
      ? 'Enregistrement en cours…'
      : isField && isTranscribing
        ? 'Transcription en cours…'
        : null

  return (
    <section className="flex flex-col gap-2">
      <div className="flex items-center justify-between gap-2">
        <label
          htmlFor="observation-text"
          className={cn('text-sm font-semibold', terrain.foreground)}
        >
          Décrivez l’observation
        </label>
        {text.length > 0 ? (
          <button
            type="button"
            className={cn(
              'shrink-0 text-xs font-medium underline-offset-2 hover:underline',
              terrain.muted,
            )}
            onClick={() => onTextChange('')}
          >
            Effacer le texte
          </button>
        ) : null}
      </div>
      <div className="relative" data-testid="report-text-field">
        <textarea
          id="observation-text"
          className={cn(
            'min-h-[150px] w-full resize-none rounded-[24px] border border-[#E8E6DF] bg-white',
            'px-4 pb-12 pt-3 pr-16 text-base leading-relaxed outline-none',
            terrain.foreground,
            'placeholder:text-[#aaa]',
            isField && 'min-h-[180px]',
          )}
          value={text}
          onChange={(event) =>
            onTextChange(event.target.value.slice(0, OBSERVATION_TEXT_MAX_LENGTH))
          }
          placeholder="Détaillez ce que vous voyez..."
        />
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
      <div className={cn('flex items-center gap-2 px-1', !isField && 'justify-end')}>
        {voiceStatus ? (
          <p
            className={cn(
              'text-xs font-medium',
              isRecording ? terrain.danger : actionPlanFeedTealTextClassName,
            )}
            role="status"
            aria-live="polite"
          >
            {voiceStatus}
          </p>
        ) : null}
        <p
          className={cn(
            isField
              ? cn('ms-auto text-[10px] tabular-nums', terrain.mutedLight)
              : cn('text-xs', terrain.muted),
          )}
        >
          {textLength}/{OBSERVATION_TEXT_MAX_LENGTH}
        </p>
      </div>
    </section>
  )
}
