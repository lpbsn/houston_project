import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Pin, PinOff } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { pinSignal, unpinSignal, SignalsApiError } from '../api'
import type { SignalDetail, SignalPinReplacementCandidate } from '../types'
import { SignalPinReplacementSheet } from '../components/signal-pin-replacement-sheet'
import { recordKeys } from './api'
import { ErrorNote } from './shared'

export function RecordPinning({
  site,
  signal,
}: {
  site: string
  signal: SignalDetail
}) {
  const client = useQueryClient()
  const [candidates, setCandidates] = useState<SignalPinReplacementCandidate[]>(
    [],
  )
  const mutation = useMutation({
    mutationFn: (replacement?: string) =>
      signal.is_pinned
        ? unpinSignal(site, signal.id)
        : pinSignal(site, signal.id, { replacePinId: replacement }),
    onSuccess: async () => {
      setCandidates([])
      await client.invalidateQueries({ queryKey: recordKeys.all(site) })
      await client.invalidateQueries({ queryKey: ['signals'] })
    },
    onError: (error) => {
      if (error instanceof SignalsApiError && error.code === 'signal_pin_limit')
        setCandidates(error.replacementCandidates)
    },
  })
  if (!signal.permission_hints.can_pin) return null
  return (
    <>
      <Button
        variant="outline"
        disabled={mutation.isPending}
        onClick={() => mutation.mutate(undefined)}
      >
        {signal.is_pinned ? <PinOff size={15} /> : <Pin size={15} />}
        {signal.is_pinned ? 'Désépingler' : 'Épingler'}
      </Button>
      {!candidates.length && <ErrorNote error={mutation.error} />}
      <SignalPinReplacementSheet
        open={candidates.length > 0}
        candidates={candidates}
        isPending={mutation.isPending}
        onClose={() => setCandidates([])}
        onReplace={(id) => mutation.mutate(id)}
      />
    </>
  )
}
