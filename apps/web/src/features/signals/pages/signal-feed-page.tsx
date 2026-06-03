import { useState } from 'react'
import { LoaderCircle } from 'lucide-react'
import { motion } from 'framer-motion'

import { useAuth } from '@/app/auth-provider'
import { Button } from '@/components/ui/button'

import { SignalCard } from '../components/signal-card'
import { SignalFeedTabs } from '../components/signal-feed-tabs'
import { useSignalFeedQuery } from '../hooks'
import { SignalsApiError } from '../api'
import type { SignalViewMode } from '../types'

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
    return <p className="text-sm text-[#6b5f52]">Établissement non sélectionné.</p>
  }

  return (
    <div className="flex flex-col gap-4">
      <SignalFeedTabs viewMode={viewMode} onChange={setViewMode} />

      {feedQuery.isLoading ? (
        <div className="flex items-center justify-center py-16 text-[#6b5f52]">
          <LoaderCircle className="h-6 w-6 animate-spin" />
        </div>
      ) : null}

      {feedQuery.isError ? (
        <div className="rounded-2xl border border-[#f0c4c4] bg-[#fff5f5] p-4 text-sm text-[#a32d2d]">
          {getErrorMessage(feedQuery.error)}
          <Button
            type="button"
            variant="outline"
            className="mt-3 rounded-xl"
            onClick={() => void feedQuery.refetch()}
          >
            Réessayer
          </Button>
        </div>
      ) : null}

      {feedQuery.isSuccess && feedQuery.data.items.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-[#e7dfd1] bg-[#fffaf2] p-8 text-center">
          <p className="text-sm font-medium text-[#4a4034]">Aucun signal actif</p>
          <p className="mt-1 text-xs text-[#9a8f82]">
            {viewMode === 'personal'
              ? 'Aucun signal ne correspond à votre zone pour le moment.'
              : 'Aucun signal actif dans cet établissement.'}
          </p>
        </div>
      ) : null}

      {feedQuery.isSuccess && feedQuery.data.items.length > 0 ? (
        <motion.div className="flex flex-col gap-3" layout>
          {feedQuery.data.items.map((item) => (
            <SignalCard key={item.id} item={item} onSelect={onOpenSignal} />
          ))}
        </motion.div>
      ) : null}
    </div>
  )
}
