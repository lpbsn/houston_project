import { useEffect } from 'react'
import { PinOff, X } from 'lucide-react'

import { TerrainBottomSheet } from '@/components/ui/terrain'

import { formatSignalPinnedByLine } from '../lib/signal-display'
import type { SignalPinReplacementCandidate } from '../types'

type SignalPinReplacementSheetProps = {
  open: boolean
  candidates: SignalPinReplacementCandidate[]
  isPending: boolean
  presentation?: 'sheet' | 'dialog'
  onClose: () => void
  onReplace: (signalId: string) => void
}

export function SignalPinReplacementSheet({
  open,
  candidates,
  isPending,
  presentation = 'sheet',
  onClose,
  onReplace,
}: SignalPinReplacementSheetProps) {
  useEffect(() => {
    if (!open || isPending || presentation !== 'dialog') {
      return
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        onClose()
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [isPending, onClose, open, presentation])

  if (!open) {
    return null
  }

  const choices = (
    <div className="flex flex-col gap-3">
      <p className="text-sm text-[#5c564e]">
        Cinq observations sont déjà épinglées. Choisissez celle à remplacer.
      </p>
      <ul className="flex flex-col gap-2">
        {candidates.map((candidate) => {
          const pinnedBy = formatSignalPinnedByLine(candidate)
          return (
            <li key={candidate.signal_id}>
              <button
                type="button"
                className="flex min-h-11 w-full items-center gap-3 rounded-lg border border-[#E8E6DF] bg-[#F5F4F0] px-3 py-2.5 text-left disabled:cursor-not-allowed disabled:opacity-50"
                disabled={isPending}
                onClick={() => onReplace(candidate.signal_id)}
              >
                <PinOff className="size-4 shrink-0 text-[#5c564e]" aria-hidden />
                <span className="min-w-0 flex-1">
                  <span className="block text-sm font-medium text-[#1a1a1a]">
                    {candidate.title}
                  </span>
                  {pinnedBy ? (
                    <span className="mt-0.5 block text-[11px] text-[#7D7B75]">{pinnedBy}</span>
                  ) : null}
                </span>
              </button>
            </li>
          )
        })}
      </ul>
    </div>
  )

  if (presentation === 'dialog') {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="signal-pin-replacement-title"
          className="w-full max-w-sm rounded-lg border border-[#E8E6DF] bg-white p-4 shadow-lg"
        >
          <div className="mb-3 flex items-center justify-between gap-3">
            <h2 id="signal-pin-replacement-title" className="text-sm font-semibold text-[#1a1a1a]">
              Remplacer une épingle
            </h2>
            <button
              type="button"
              className="inline-flex size-9 items-center justify-center rounded-md text-[#5c564e] hover:bg-[#F5F4F0] disabled:opacity-50"
              aria-label="Fermer"
              disabled={isPending}
              onClick={onClose}
            >
              <X className="size-4" aria-hidden />
            </button>
          </div>
          {choices}
        </div>
      </div>
    )
  }

  return (
    <TerrainBottomSheet title="Remplacer une épingle" open dismissible={!isPending} onClose={onClose}>
      {choices}
    </TerrainBottomSheet>
  )
}
