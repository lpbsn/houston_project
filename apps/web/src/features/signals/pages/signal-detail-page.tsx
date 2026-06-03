import { ArrowLeft, LoaderCircle } from 'lucide-react'

import { useAuth } from '@/app/auth-provider'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'

import { SignalPinUrgencyActions } from '../components/signal-pin-urgency-actions'
import { SignalStatusBadge } from '../components/signal-status-badge'
import { SignalTaxonomyBadges } from '../components/signal-taxonomy-badges'
import { SignalUrgencyBadge } from '../components/signal-urgency-badge'
import {
  usePinSignalMutation,
  useSignalDetailQuery,
  useSignalUrgencyMutation,
  useUnpinSignalMutation,
} from '../hooks'
import { SignalsApiError } from '../api'

type SignalDetailPageProps = {
  signalId: string
  onBack: () => void
}

function getErrorMessage(error: unknown): string {
  if (error instanceof SignalsApiError) {
    return error.detail
  }
  if (error instanceof Error) {
    return error.message
  }
  return 'Une erreur est survenue.'
}

export function SignalDetailPage({ signalId, onBack }: SignalDetailPageProps) {
  const auth = useAuth()
  const establishmentId = auth.bootstrap?.active_membership?.establishment_id ?? null

  const detailQuery = useSignalDetailQuery(establishmentId, signalId)
  const pinMutation = usePinSignalMutation(establishmentId, signalId)
  const unpinMutation = useUnpinSignalMutation(establishmentId, signalId)
  const urgencyMutation = useSignalUrgencyMutation(establishmentId, signalId)

  const isPending =
    pinMutation.isPending || unpinMutation.isPending || urgencyMutation.isPending

  if (detailQuery.isLoading) {
    return (
      <div className="flex items-center justify-center py-16 text-[#6b5f52]">
        <LoaderCircle className="h-6 w-6 animate-spin" />
      </div>
    )
  }

  if (detailQuery.isError || !detailQuery.data) {
    return (
      <div className="space-y-4">
        <Button type="button" variant="ghost" className="rounded-xl px-0" onClick={onBack}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Retour
        </Button>
        <p className="text-sm text-[#a32d2d]">{getErrorMessage(detailQuery.error)}</p>
      </div>
    )
  }

  const signal = detailQuery.data

  return (
    <div className="flex flex-col gap-4">
      <Button type="button" variant="ghost" className="w-fit rounded-xl px-0" onClick={onBack}>
        <ArrowLeft className="mr-2 h-4 w-4" />
        Retour
      </Button>

      <Card className="gap-4 rounded-2xl border border-[#e7dfd1] bg-white p-4">
        <div className="flex flex-wrap gap-2">
          <SignalUrgencyBadge urgency={signal.urgency} />
          <SignalTaxonomyBadges domainKey={signal.domain_key} subjectKey={signal.subject_key} />
          <SignalStatusBadge status={signal.status} />
        </div>
        <h2 className="text-xl font-semibold text-[#2a2218]">{signal.title}</h2>
        {signal.location_text ? (
          <p className="text-xs text-[#9a8f82]">📍 {signal.location_text}</p>
        ) : null}
        {signal.source_context.reporter_display_name ? (
          <p className="text-xs text-[#9a8f82]">
            Signalé par {signal.source_context.reporter_display_name}
          </p>
        ) : null}
      </Card>

      <Card className="gap-2 rounded-2xl border border-[#e7dfd1] bg-[#fffaf2] p-4">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-[#9a8f82]">
          Résumé structuré
        </h3>
        <p className="text-sm leading-relaxed text-[#4a4034]">{signal.structured_summary}</p>
      </Card>

      {signal.source_context.media_count > 0 ? (
        <Card className="rounded-2xl border border-[#e7dfd1] bg-white p-4">
          <p className="text-sm text-[#6b5f52]">
            {signal.source_context.media_count} photo(s) liée(s) à l&apos;observation source.
          </p>
        </Card>
      ) : null}

      <SignalPinUrgencyActions
        hints={signal.permission_hints}
        isPinned={signal.is_pinned}
        urgency={signal.urgency}
        isPending={isPending}
        onPin={() => void pinMutation.mutate()}
        onUnpin={() => void unpinMutation.mutate()}
        onSetUrgency={(urgency) => void urgencyMutation.mutate(urgency)}
      />
    </div>
  )
}
