import { useCallback, useEffect, useRef, useState } from 'react'

import {
  subscribeAppBackground,
  subscribeAppForeground,
  usesNativeAppLifecycle,
} from '@/lib/app-lifecycle'
import { getIsOnline, subscribeNetworkOnline } from '@/lib/network-status'
import { resolveWsUrl } from '@/lib/runtime'
import { shouldResumeWsConnection } from '@/lib/ws-resume'

import { issueOperationalRealtimeWsTicket } from '../api'
import type {
  OperationalRealtimeAccessEvent,
  OperationalRealtimeConnectionStatus,
  OperationalRealtimeInvalidateEvent,
  OperationalRealtimeServerEvent,
} from '../types'

const AUTH_TIMEOUT_MS = 5000
const RECONNECT_BASE_MS = 1000
const RECONNECT_MAX_MS = 15000

function buildOperationalRealtimeWebSocketUrl(establishmentId: string): string {
  return resolveWsUrl(`/ws/v1/establishments/${establishmentId}/realtime/`)
}

function logWsCloseDev(channel: string, event: CloseEvent) {
  if (!import.meta.env.DEV) {
    return
  }

  console.info(`[houston:${channel}] ws closed`, {
    code: event.code,
    reason: event.reason,
    wasClean: event.wasClean,
  })
}

function parseServerEvent(payload: unknown): OperationalRealtimeServerEvent | null {
  if (!payload || typeof payload !== 'object') {
    return null
  }

  const event = payload as Record<string, unknown>
  if (typeof event.type !== 'string') {
    return null
  }

  return event as OperationalRealtimeServerEvent
}

type UseOperationalRealtimeWebSocketOptions = {
  establishmentId: string | null
  enabled: boolean
  onInvalidate?: (event: OperationalRealtimeInvalidateEvent) => void
  onAccess?: (event: OperationalRealtimeAccessEvent) => void
  onReconnect?: () => void
}

export function useOperationalRealtimeWebSocket({
  establishmentId,
  enabled,
  onInvalidate,
  onAccess,
  onReconnect,
}: UseOperationalRealtimeWebSocketOptions) {
  const [connectionStatus, setConnectionStatusState] =
    useState<OperationalRealtimeConnectionStatus>('idle')
  const socketRef = useRef<WebSocket | null>(null)
  const reconnectAttemptRef = useRef(0)
  const reconnectTimerRef = useRef<number | null>(null)
  const intentionalCloseRef = useRef(false)
  const resumeBlockedRef = useRef(false)
  const suspendedRef = useRef(false)
  const hasConnectedOnceRef = useRef(false)
  const connectRef = useRef<(() => Promise<void>) | null>(null)
  const connectGenerationRef = useRef(0)
  const connectionStatusRef = useRef<OperationalRealtimeConnectionStatus>('idle')
  const enabledRef = useRef(enabled)

  const setConnectionStatus = useCallback((status: OperationalRealtimeConnectionStatus) => {
    connectionStatusRef.current = status
    setConnectionStatusState(status)
  }, [])

  const onInvalidateRef = useRef(onInvalidate)
  const onAccessRef = useRef(onAccess)
  const onReconnectRef = useRef(onReconnect)

  useEffect(() => {
    enabledRef.current = enabled
  }, [enabled])

  useEffect(() => {
    onInvalidateRef.current = onInvalidate
    onAccessRef.current = onAccess
    onReconnectRef.current = onReconnect
  }, [onAccess, onInvalidate, onReconnect])

  const clearReconnectTimer = useCallback(() => {
    if (reconnectTimerRef.current !== null) {
      window.clearTimeout(reconnectTimerRef.current)
      reconnectTimerRef.current = null
    }
  }, [])

  const closeSocket = useCallback(() => {
    const socket = socketRef.current
    socketRef.current = null
    if (!socket) {
      return
    }
    if (socket.readyState === WebSocket.CONNECTING || socket.readyState === WebSocket.OPEN) {
      socket.close()
    }
  }, [])

  const scheduleReconnect = useCallback(() => {
    setConnectionStatus('reconnecting')
    const delay = Math.min(
      RECONNECT_BASE_MS * 2 ** reconnectAttemptRef.current,
      RECONNECT_MAX_MS,
    )
    reconnectAttemptRef.current += 1
    reconnectTimerRef.current = window.setTimeout(() => {
      void connectRef.current?.()
    }, delay)
  }, [setConnectionStatus])

  const connect = useCallback(async () => {
    if (!establishmentId || !enabled || resumeBlockedRef.current || suspendedRef.current) {
      return
    }

    const generation = ++connectGenerationRef.current

    clearReconnectTimer()
    closeSocket()

    const isReconnect = hasConnectedOnceRef.current
    setConnectionStatus(isReconnect ? 'reconnecting' : 'connecting')

    try {
      const ticketResponse = await issueOperationalRealtimeWsTicket(establishmentId)
      if (
        generation !== connectGenerationRef.current ||
        suspendedRef.current ||
        resumeBlockedRef.current
      ) {
        return
      }

      const socket = new WebSocket(buildOperationalRealtimeWebSocketUrl(establishmentId))
      if (
        generation !== connectGenerationRef.current ||
        suspendedRef.current ||
        resumeBlockedRef.current
      ) {
        socket.close()
        return
      }

      socketRef.current = socket
      let authTimer: number | null = null

      const sendAuth = () => {
        if (socketRef.current !== socket) {
          return
        }

        socket.send(
          JSON.stringify({
            type: 'auth',
            ticket: ticketResponse.ticket,
          }),
        )

        if (authTimer === null) {
          authTimer = window.setTimeout(() => {
            if (socketRef.current === socket) {
              socket.close()
            }
          }, AUTH_TIMEOUT_MS)
        }
      }

      socket.onopen = sendAuth
      if (socket.readyState === WebSocket.OPEN) {
        sendAuth()
      }

      socket.onmessage = (event) => {
        let payload: unknown
        try {
          payload = JSON.parse(String(event.data))
        } catch {
          return
        }

        const parsed = parseServerEvent(payload)
        if (!parsed) {
          return
        }

        if (parsed.type === 'auth.ok') {
          if (authTimer !== null) {
            window.clearTimeout(authTimer)
            authTimer = null
          }
          hasConnectedOnceRef.current = true
          reconnectAttemptRef.current = 0
          setConnectionStatus('connected')
          if (isReconnect) {
            onReconnectRef.current?.()
          }
          return
        }

        if (parsed.type === 'invalidate') {
          onInvalidateRef.current?.(parsed)
          return
        }

        if (parsed.type === 'access') {
          if (parsed.reason === 'session.revoked') {
            resumeBlockedRef.current = true
            intentionalCloseRef.current = true
          }
          onAccessRef.current?.(parsed)
        }
      }

      socket.onclose = (event) => {
        if (socketRef.current !== socket) {
          return
        }

        if (authTimer !== null) {
          window.clearTimeout(authTimer)
          authTimer = null
        }

        socketRef.current = null
        logWsCloseDev('realtime', event)

        if (
          resumeBlockedRef.current ||
          suspendedRef.current ||
          intentionalCloseRef.current ||
          !enabledRef.current
        ) {
          intentionalCloseRef.current = false
          setConnectionStatus('disconnected')
          return
        }

        scheduleReconnect()
      }

      socket.onerror = () => {
        // onclose handles reconnection
      }
    } catch {
      if (
        generation === connectGenerationRef.current &&
        !suspendedRef.current &&
        !resumeBlockedRef.current
      ) {
        scheduleReconnect()
      }
    }
  }, [clearReconnectTimer, closeSocket, enabled, establishmentId, scheduleReconnect, setConnectionStatus])

  useEffect(() => {
    connectRef.current = connect
  }, [connect])

  useEffect(() => {
    intentionalCloseRef.current = false
    resumeBlockedRef.current = false
    suspendedRef.current = false
    hasConnectedOnceRef.current = false
    reconnectAttemptRef.current = 0

    if (!establishmentId || !enabled) {
      clearReconnectTimer()
      closeSocket()
      return
    }

    void connect()

    return () => {
      intentionalCloseRef.current = true
      clearReconnectTimer()
      closeSocket()
    }
  }, [clearReconnectTimer, closeSocket, connect, enabled, establishmentId])

  useEffect(() => {
    if (!establishmentId || !enabled) {
      return
    }

    const resume = (force: boolean) => {
      if (
        !shouldResumeWsConnection({
          enabled: enabledRef.current,
          resumeBlocked: resumeBlockedRef.current,
          suspended: suspendedRef.current,
          force,
          isConnected:
            connectionStatusRef.current === 'connected' && socketRef.current !== null,
        })
      ) {
        return
      }
      suspendedRef.current = false
      void connectRef.current?.()
    }

    const unsubscribeForeground = subscribeAppForeground(() => {
      const native = usesNativeAppLifecycle()
      if (native) {
        suspendedRef.current = false
        if (!getIsOnline()) {
          return
        }
      }
      resume(native)
    })
    const unsubscribeBackground = subscribeAppBackground(() => {
      if (!usesNativeAppLifecycle()) {
        return
      }
      suspendedRef.current = true
      clearReconnectTimer()
      closeSocket()
    })
    const unsubscribeOnline = subscribeNetworkOnline(() => {
      resume(false)
    })

    return () => {
      unsubscribeForeground()
      unsubscribeBackground()
      unsubscribeOnline()
    }
  }, [clearReconnectTimer, closeSocket, enabled, establishmentId])

  const requestIntentionalClose = useCallback(() => {
    resumeBlockedRef.current = true
    intentionalCloseRef.current = true
    closeSocket()
  }, [closeSocket])

  return {
    connectionStatus: enabled ? connectionStatus : 'idle',
    requestIntentionalClose,
    reconnect: connect,
  }
}
