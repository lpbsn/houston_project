import { useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import { notifySuccess } from '@/lib/success-toast'

import { SignalsApiError } from '../api'
import {
  prefetchSignalDetail,
  removeQualifiedSourceSignalDetailCache,
  useQualifySignalRoutingMutation,
  useSignalDetailQuery,
} from '../hooks'
import { mapSignalQualifyError } from '../lib/map-signal-qualify-error'
import type { SignalQualifyRoutingRequest } from '../types'

type UseSignalQualifySheetOptions = {
  establishmentId: string | null
  onNavigate: (pathname: string, options?: { replace?: boolean }) => void
}

export function useSignalQualifySheet({
  establishmentId,
  onNavigate,
}: UseSignalQualifySheetOptions) {
  const queryClient = useQueryClient()
  const [signalId, setSignalId] = useState<string | null>(null)
  const [open, setOpen] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [opening, setOpening] = useState(false)

  const detailQuery = useSignalDetailQuery(establishmentId, signalId)
  const mutation = useQualifySignalRoutingMutation(establishmentId)

  async function openForSignal(nextSignalId: string) {
    if (!establishmentId) {
      return
    }
    setErrorMessage(null)
    setSignalId(nextSignalId)
    setOpening(true)
    try {
      await prefetchSignalDetail(queryClient, establishmentId, nextSignalId)
      setOpen(true)
    } catch (error) {
      const mapped = mapSignalQualifyError({
        code: error instanceof SignalsApiError ? error.code : null,
        detail: error instanceof SignalsApiError ? error.detail : null,
        payload: error instanceof SignalsApiError ? error.payload : undefined,
      })
      setErrorMessage(mapped.message)
      setOpen(false)
    } finally {
      setOpening(false)
    }
  }

  function close() {
    if (mutation.isPending) {
      return
    }
    setOpen(false)
    setErrorMessage(null)
    setSignalId(null)
  }

  function handleMergedNavigation(sourceSignalId: string, survivingSignalId: string) {
    notifySuccess({ message: 'Observation fusionnée.', kind: 'updated' })
    onNavigate(`/signals/${survivingSignalId}`, { replace: true })
    if (establishmentId) {
      removeQualifiedSourceSignalDetailCache(
        queryClient,
        establishmentId,
        sourceSignalId,
        survivingSignalId,
      )
    }
  }

  async function submit(body: SignalQualifyRoutingRequest) {
    if (!signalId || !establishmentId) {
      return
    }
    setErrorMessage(null)
    try {
      const result = await mutation.mutateAsync({ signalId, body })
      if (result.qualification_outcome === 'merged') {
        const sourceId = signalId
        setOpen(false)
        setSignalId(null)
        handleMergedNavigation(sourceId, result.surviving_signal_id)
        return
      }
      notifySuccess({ message: 'Routage mis à jour.', kind: 'updated' })
      setOpen(false)
      setSignalId(null)
    } catch (error) {
      if (error instanceof SignalsApiError) {
        const mapped = mapSignalQualifyError({
          code: error.code,
          detail: error.detail,
          payload: error.payload,
        })
        if (error.code === 'already_merged' && mapped.survivingSignalId) {
          const sourceId = signalId
          setOpen(false)
          setSignalId(null)
          handleMergedNavigation(sourceId, mapped.survivingSignalId)
          return
        }
        setErrorMessage(mapped.message)
        return
      }
      setErrorMessage('La qualification a échoué.')
    }
  }

  return {
    open,
    opening,
    signalId,
    signal: detailQuery.data ?? null,
    isPending: mutation.isPending || opening || (open && detailQuery.isFetching),
    errorMessage:
      errorMessage ??
      (detailQuery.isError ? 'Impossible de charger l’observation.' : null),
    openForSignal,
    close,
    submit,
  }
}
