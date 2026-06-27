import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  type PropsWithChildren,
} from 'react'
import { useQueryClient } from '@tanstack/react-query'

import { useOperationalRealtimeWebSocket } from '../hooks/use-operational-realtime-websocket'
import {
  applyOperationalInvalidation,
  applyOperationalReconnectInvalidation,
} from '../lib/apply-operational-invalidation'
import { applyRealtimeAccessEvent } from '../lib/apply-realtime-access-events'
import type {
  OperationalRealtimeAccessEvent,
  OperationalRealtimeConnectionStatus,
  OperationalRealtimeInvalidateEvent,
} from '../types'

type OperationalRealtimeContextValue = {
  connectionStatus: OperationalRealtimeConnectionStatus
}

const OperationalRealtimeContext = createContext<OperationalRealtimeContextValue | null>(null)

type OperationalRealtimeProviderProps = PropsWithChildren<{
  establishmentId: string | null
  activeMembershipId: string | null
  enabled: boolean
  onActiveMembershipDeactivated?: () => void
}>

export function OperationalRealtimeProvider({
  establishmentId,
  activeMembershipId,
  enabled,
  onActiveMembershipDeactivated,
  children,
}: OperationalRealtimeProviderProps) {
  const queryClient = useQueryClient()
  const intentionalCloseRef = useRef<() => void>(() => {})

  const handleInvalidate = useCallback(
    (event: OperationalRealtimeInvalidateEvent) => {
      if (!establishmentId) {
        return
      }
      applyOperationalInvalidation(event, { queryClient, establishmentId })
    },
    [establishmentId, queryClient],
  )

  const handleAccess = useCallback(
    (event: OperationalRealtimeAccessEvent) => {
      if (!establishmentId) {
        return
      }
      applyRealtimeAccessEvent(event, {
        queryClient,
        establishmentId,
        activeMembershipId,
        onIntentionalClose: () => {
          intentionalCloseRef.current()
        },
        onActiveMembershipDeactivated: () => {
          onActiveMembershipDeactivated?.()
        },
      })
    },
    [activeMembershipId, establishmentId, onActiveMembershipDeactivated, queryClient],
  )

  const handleReconnect = useCallback(() => {
    if (!establishmentId) {
      return
    }
    applyOperationalReconnectInvalidation(queryClient, establishmentId)
  }, [establishmentId, queryClient])

  const { connectionStatus, requestIntentionalClose } = useOperationalRealtimeWebSocket({
    establishmentId,
    enabled,
    onInvalidate: handleInvalidate,
    onAccess: handleAccess,
    onReconnect: handleReconnect,
  })

  useEffect(() => {
    intentionalCloseRef.current = requestIntentionalClose
  }, [requestIntentionalClose])

  const value = useMemo(
    () => ({
      connectionStatus,
    }),
    [connectionStatus],
  )

  return (
    <OperationalRealtimeContext.Provider value={value}>{children}</OperationalRealtimeContext.Provider>
  )
}

export function useOperationalRealtime(): OperationalRealtimeContextValue {
  const context = useContext(OperationalRealtimeContext)
  if (!context) {
    throw new Error('useOperationalRealtime must be used within OperationalRealtimeProvider.')
  }
  return context
}

export function useOptionalOperationalRealtime(): OperationalRealtimeContextValue | null {
  return useContext(OperationalRealtimeContext)
}
