import { useCallback, useEffect, useRef, useState } from 'react'

import { issueChatWsTicket } from '../api'
import type {
  ChatConnectionStatus,
  ChatWsAccessRevokedEvent,
  ChatWsMessageCreatedEvent,
  ChatWsMessageRejectedEvent,
  ChatWsServerEvent,
} from '../types'

const AUTH_TIMEOUT_MS = 5000
const RECONNECT_BASE_MS = 1000
const RECONNECT_MAX_MS = 15000

function buildChatWebSocketUrl(establishmentId: string): string {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}/ws/v1/establishments/${establishmentId}/chat/`
}

function parseServerEvent(payload: unknown): ChatWsServerEvent | null {
  if (!payload || typeof payload !== 'object') {
    return null
  }

  const event = payload as Record<string, unknown>
  if (typeof event.type !== 'string') {
    return null
  }

  return event as ChatWsServerEvent
}

type UseChatWebSocketOptions = {
  establishmentId: string | null
  enabled: boolean
  onMessageCreated?: (event: ChatWsMessageCreatedEvent) => void
  onMessageRejected?: (event: ChatWsMessageRejectedEvent) => void
  onAccessRevoked?: (event: ChatWsAccessRevokedEvent) => void
  onReconnect?: () => void
}

export function useChatWebSocket({
  establishmentId,
  enabled,
  onMessageCreated,
  onMessageRejected,
  onAccessRevoked,
  onReconnect,
}: UseChatWebSocketOptions) {
  const [connectionStatus, setConnectionStatus] = useState<ChatConnectionStatus>('idle')
  const socketRef = useRef<WebSocket | null>(null)
  const reconnectAttemptRef = useRef(0)
  const reconnectTimerRef = useRef<number | null>(null)
  const intentionalCloseRef = useRef(false)
  const hasConnectedOnceRef = useRef(false)
  const connectRef = useRef<(() => Promise<void>) | null>(null)

  const onMessageCreatedRef = useRef(onMessageCreated)
  const onMessageRejectedRef = useRef(onMessageRejected)
  const onAccessRevokedRef = useRef(onAccessRevoked)
  const onReconnectRef = useRef(onReconnect)

  useEffect(() => {
    onMessageCreatedRef.current = onMessageCreated
    onMessageRejectedRef.current = onMessageRejected
    onAccessRevokedRef.current = onAccessRevoked
    onReconnectRef.current = onReconnect
  }, [onAccessRevoked, onMessageCreated, onMessageRejected, onReconnect])

  const clearReconnectTimer = useCallback(() => {
    if (reconnectTimerRef.current !== null) {
      window.clearTimeout(reconnectTimerRef.current)
      reconnectTimerRef.current = null
    }
  }, [])

  const closeSocket = useCallback(() => {
    const socket = socketRef.current
    socketRef.current = null
    if (socket && socket.readyState === WebSocket.OPEN) {
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
  }, [])

  const connect = useCallback(async () => {
    if (!establishmentId || !enabled) {
      return
    }

    clearReconnectTimer()
    closeSocket()

    const isReconnect = hasConnectedOnceRef.current
    setConnectionStatus(isReconnect ? 'reconnecting' : 'connecting')

    try {
      const ticketResponse = await issueChatWsTicket(establishmentId)
      const socket = new WebSocket(buildChatWebSocketUrl(establishmentId))
      socketRef.current = socket

      let authTimer: number | null = window.setTimeout(() => {
        intentionalCloseRef.current = true
        socket.close()
      }, AUTH_TIMEOUT_MS)

      socket.onopen = () => {
        socket.send(
          JSON.stringify({
            type: 'auth',
            ticket: ticketResponse.ticket,
          }),
        )
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

        if (parsed.type === 'message.created') {
          onMessageCreatedRef.current?.(parsed)
          return
        }

        if (parsed.type === 'message.rejected') {
          onMessageRejectedRef.current?.(parsed)
          return
        }

        if (parsed.type === 'conversation.access_revoked') {
          onAccessRevokedRef.current?.(parsed)
        }
      }

      socket.onclose = () => {
        if (authTimer !== null) {
          window.clearTimeout(authTimer)
          authTimer = null
        }

        socketRef.current = null

        if (intentionalCloseRef.current || !enabled) {
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
      scheduleReconnect()
    }
  }, [clearReconnectTimer, closeSocket, enabled, establishmentId, scheduleReconnect])

  useEffect(() => {
    connectRef.current = connect
  }, [connect])

  useEffect(() => {
    intentionalCloseRef.current = false
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

  const sendMessage = useCallback(
    (payload: { conversationId: string; clientMessageId: string; body: string }) => {
      const socket = socketRef.current
      if (!socket || socket.readyState !== WebSocket.OPEN || connectionStatus !== 'connected') {
        return false
      }

      socket.send(
        JSON.stringify({
          type: 'message.send',
          conversation_id: payload.conversationId,
          client_message_id: payload.clientMessageId,
          body: payload.body,
        }),
      )
      return true
    },
    [connectionStatus],
  )

  return {
    connectionStatus: enabled ? connectionStatus : 'idle',
    sendMessage,
    reconnect: connect,
  }
}
