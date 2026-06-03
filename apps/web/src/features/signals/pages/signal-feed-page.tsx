import { useState } from 'react'
import { LoaderCircle } from 'lucide-react'

import { useAuth } from '@/app/auth-provider'
import {
  TerrainEmptyState,
  TerrainErrorState,
  TerrainSectionLabel,
} from '@/components/ui/terrain'
import { SignalCard } from '../components/signal-card'
import { SignalFeedFiltersPlaceholder } from '../components/signal-feed-filters-placeholder'
import { SignalFeedTabs } from '../components/signal-feed-tabs'
import { useSignalFeedQuery } from '../hooks'
import { SignalsApiError } from '../api'
import { groupFeedItemsByStatus } from '../lib/signal-display'
import type { SignalFeedItem, SignalViewMode } from '../types'

type SignalFeedPageProps = {
  onOpenSignal: (signalId: string) => void
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

export function SignalFeedPage({ onOpenSignal }: SignalFeedPageProps) {
  const auth = useAuth()
  const establishmentId = auth.bootstrap?.active_membership?.establishment_id ?? null
  const [viewMode, setViewMode] = useState<SignalViewMode>('personal')

  const feedQuery = useSignalFeedQuery(establishmentId, viewMode)

  if (!establishmentId) {
    return (
      <p className="px-3 py-4 text-sm text-[#6b5f52]">Établissement non sélectionné.</p>
    )
  }

  const groups =
    feedQuery.isSuccess && feedQuery.data.items.length > 0
      ? groupFeedItemsByStatus(feedQuery.data.items)
      : null

  const listClassName = 'flex flex-col gap-3 px-3'

  const renderItems = (items: SignalFeedItem[]) => (
    <div className={listClassName}>
      {items.map((item) => (
        <SignalCard key={item.id} item={item} onSelect={onOpenSignal} />
      ))}
    </div>
  )

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="shrink-0 border-b border-[#E8E6DF] bg-white">
        <div className="px-3 pb-3 pt-1">
          <SignalFeedTabs viewMode={viewMode} onChange={setViewMode} />
        </div>
        <SignalFeedFiltersPlaceholder />
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto overscroll-y-contain pb-3">
        {feedQuery.isLoading ? (
          <div className="flex items-center justify-center py-16 text-[#7D7B75]">
            <LoaderCircle className="h-6 w-6 animate-spin" />
          </div>
        ) : null}

        {feedQuery.isError ? (
          <TerrainErrorState
            className="mx-3 mt-3"
            message={getErrorMessage(feedQuery.error)}
            onRetry={() => void feedQuery.refetch()}
          />
        ) : null}

        {feedQuery.isSuccess && feedQuery.data.items.length === 0 ? (
          <TerrainEmptyState
            className="mx-3 mt-3"
            title="Aucun signal actif"
            description={
              viewMode === 'personal'
                ? 'Aucun signal ne correspond à votre zone pour le moment.'
                : 'Aucun signal actif dans cet établissement.'
            }
          />
        ) : null}

        {feedQuery.isSuccess && feedQuery.data.items.length > 0 && groups ? (
          <div className="flex flex-col gap-3 pt-5">
            {groups.map((group) => (
              <section key={group.status}>
                <TerrainSectionLabel dotVariant={group.dotVariant} className="px-3">
                  {group.label} · {group.items.length}
                </TerrainSectionLabel>
                {renderItems(group.items)}
              </section>
            ))}
          </div>
        ) : null}

        {feedQuery.isSuccess && feedQuery.data.items.length > 0 && !groups ? (
          <div className="pt-5">{renderItems(feedQuery.data.items)}</div>
        ) : null}
      </div>
    </div>
  )
}
