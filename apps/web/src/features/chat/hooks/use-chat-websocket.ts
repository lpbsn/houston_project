import { useCallback, useEffect, useRef, useState } from 'react'

import {
  subscribeAppBackground,
  subscribeAppForeground,
  usesNativeAppLifecycle,
} from '@/lib/app-lifecycle'
import { subscribeNetworkOnline } from '@/lib/network-status'
import { resolveWsUrl } from '@/lib/runtime'
import { shouldResumeWsConnection } from '@/lib/ws-resume'

import { issueChatWsTicket } from '../api'
import type {
  ChatConnectionStatus,
  ChatWsConversationAccessRevokedEvent,
  ChatWsConversationUpdatedEvent,
  ChatWsGlobalAccessRevokedEvent,
  ChatWsMessageCreatedEvent,
  ChatWsMessageRejectedEvent,
  ChatWsServerEvent,
} from '../types'

const AUTH_TIMEOUT_MS = 5000
const RECONNECT_BASE_MS = 1000
const RECONNECT_MAX_MS = 15000

function buildChatWebSocketUrl(establishmentId: string): string {
  return resolveWsUrl(`/ws/v1/establishments/${establishmentId}/chat/`)
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
  onGlobalAccessRevoked?: (event: ChatWsGlobalAccessRevokedEvent) => void
  onConversationAccessRevoked?: (event: ChatWsConversationAccessRevokedEvent) => void
  onConversationUpdated?: (event: ChatWsConversationUpdatedEvent) => void
  onReconnect?: () => void
}

export function useChatWebSocket({
  establishmentId,
  enabled,
  onMessageCreated,
  onMessageRejected,
  onGlobalAccessRevoked,
  onConversationAccessRevoked,
  onConversationUpdated,
  onReconnect,
}: UseChatWebSocketOptions) {
  const [connectionStatus, setConnectionStatusState] = useState<ChatConnectionStatus>('idle')
  const socketRef = useRef<WebSocket | null>(null)
  const reconnectAttemptRef = useRef(0)
  const reconnectTimerRef = useRef<number | null>(null)
  const intentionalCloseRef = useRef(false)
  const resumeBlockedRef = useRef(false)
  const suspendedRef = useRef(false)
  const hasConnectedOnceRef = useRef(false)
  const connectRef = useRef<(() => Promise<void>) | null>(null)
  const connectGenerationRef = useRef(0)
  const connectionStatusRef = useRef<ChatConnectionStatus>('idle')
  const enabledRef = useRef(enabled)

  const setConnectionStatus = useCallback((status: ChatConnectionStatus) => {
    connectionStatusRef.current = status
    setConnectionStatusState(status)
  }, [])

  const onMessageCreatedRef = useRef(onMessageCreated)
  const onMessageRejectedRef = useRef(onMessageRejected)
  const onGlobalAccessRevokedRef = useRef(onGlobalAccessRevoked)
  const onConversationAccessRevokedRef = useRef(onConversationAccessRevoked)
  const onConversationUpdatedRef = useRef(onConversationUpdated)
  const onReconnectRef = useRef(onReconnect)

  useEffect(() => {
    enabledRef.current = enabled
  }, [enabled])

  useEffect(() => {
    onMessageCreatedRef.current = onMessageCreated
    onMessageRejectedRef.current = onMessageRejected
    onGlobalAccessRevokedRef.current = onGlobalAccessRevoked
    onConversationAccessRevokedRef.current = onConversationAccessRevoked
    onConversationUpdatedRef.current = onConversationUpdated
    onReconnectRef.current = onReconnect
  }, [
    onConversationAccessRevoked,
    onConversationUpdated,
    onGlobalAccessRevoked,
    onMessageCreated,
    onMessageRejected,
    onReconnect,
  ])

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
      const ticketResponse = await issueChatWsTicket(establishmentId)
      if (
        generation !== connectGenerationRef.current ||
        suspendedRef.current ||
        resumeBlockedRef.current
      ) {
        return
      }

      const socket = new WebSocket(buildChatWebSocketUrl(establishmentId))
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

        if (parsed.type === 'message.created') {
          onMessageCreatedRef.current?.(parsed)
          return
        }

        if (parsed.type === 'message.rejected') {
          onMessageRejectedRef.current?.(parsed)
          return
        }

        if (parsed.type === 'access.revoked') {
          resumeBlockedRef.current = true
          intentionalCloseRef.current = true
          onGlobalAccessRevokedRef.current?.(parsed)
          return
        }

        if (parsed.type === 'conversation.access_revoked') {
          onConversationAccessRevokedRef.current?.(parsed)
          return
        }

        if (parsed.type === 'conversation.updated') {
          onConversationUpdatedRef.current?.(parsed)
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
        logWsCloseDev('chat', event)

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
          isConnected: connectionStatusRef.current === 'connected',
        })
      ) {
        return
      }
      suspendedRef.current = false
      void connectRef.current?.()
    }

    const unsubscribeForeground = subscribeAppForeground(() => {
      resume(usesNativeAppLifecycle())
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
