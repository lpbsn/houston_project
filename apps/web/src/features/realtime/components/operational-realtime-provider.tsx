import { useCallback, useEffect, useRef, type PropsWithChildren } from 'react'
import { useQueryClient } from '@tanstack/react-query'

import { useOperationalRealtimeWebSocket } from '../hooks/use-operational-realtime-websocket'
import {
  applyOperationalInvalidation,
  applyOperationalReconnectInvalidation,
} from '../lib/apply-operational-invalidation'
import { applyRealtimeAccessEvent } from '../lib/apply-realtime-access-events'
import type { OperationalRealtimeAccessEvent, OperationalRealtimeInvalidateEvent } from '../types'

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

  const { requestIntentionalClose } = useOperationalRealtimeWebSocket({
    establishmentId,
    enabled,
    onInvalidate: handleInvalidate,
    onAccess: handleAccess,
    onReconnect: handleReconnect,
  })

  useEffect(() => {
    intentionalCloseRef.current = requestIntentionalClose
  }, [requestIntentionalClose])

  return children
}
