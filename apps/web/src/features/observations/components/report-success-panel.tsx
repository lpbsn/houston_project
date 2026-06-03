import { LoaderCircle } from 'lucide-react'

import { TerrainCard } from '@/components/ui/terrain'
import { Button } from '@/components/ui/button'
import { formatSignalSummaryLine } from '@/features/observations/processing-status-popup'
import type { ObservationProcessingStatusResponse } from '@/features/observations/types'
import { terrain } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

type ProcessingSignal = ObservationProcessingStatusResponse['signals'][number]

type ReportSuccessPanelProps = {
  observationId: string
  processingLabel: string
  processingSuccessHeadline: string | null
  showProcessingSignalList: boolean
  processingSignals: ProcessingSignal[]
  isProcessingLoading: boolean
  processingErrorMessage: string | null
  showSignalFeedLink: boolean
  onGoToSignalFeed?: () => void
  onNewObservation: () => void
}

export function ReportSuccessPanel({
  observationId,
  processingLabel,
  processingSuccessHeadline,
  showProcessingSignalList,
  processingSignals,
  isProcessingLoading,
  processingErrorMessage,
  showSignalFeedLink,
  onGoToSignalFeed,
  onNewObservation,
}: ReportSuccessPanelProps) {
  return (
    <TerrainCard className={terrain.successSurface}>
      <h2 className={cn('text-lg font-semibold', terrain.foreground)}>Signalement envoyé</h2>
      <div className={cn('mt-2 flex items-center gap-2 text-sm', terrain.muted)}>
        {isProcessingLoading ? (
          <LoaderCircle className="h-4 w-4 shrink-0 animate-spin" />
        ) : null}
        <p>{processingLabel}</p>
      </div>
      {processingSuccessHeadline ? (
        <p className={cn('mt-2 text-sm font-medium', terrain.foreground)}>
          {processingSuccessHeadline}
        </p>
      ) : null}
      {showProcessingSignalList && processingSignals.length > 0 ? (
        <ul className={cn('mt-2 list-disc space-y-1 pl-5 text-sm', terrain.muted)}>
          {processingSignals.map((signal) => (
            <li key={signal.id}>{formatSignalSummaryLine(signal)}</li>
          ))}
        </ul>
      ) : null}
      {processingErrorMessage ? (
        <p className="mt-2 text-sm text-[#9a3b2e]">{processingErrorMessage}</p>
      ) : null}
      <p className={cn('mt-1 text-xs', terrain.muted)}>Référence : {observationId}</p>
      {showSignalFeedLink && onGoToSignalFeed ? (
        <Button
          type="button"
          variant="outline"
          className="mt-4 h-11 w-full rounded-2xl border-[#E8E6DF]"
          onClick={onGoToSignalFeed}
        >
          Voir les signaux
        </Button>
      ) : null}
      <Button
        type="button"
        className={cn(
          'mt-3 h-11 w-full rounded-2xl text-white hover:bg-[#1B4FD8]/95',
          terrain.primaryBg,
        )}
        onClick={onNewObservation}
      >
        Nouveau signal
      </Button>
    </TerrainCard>
  )
}
