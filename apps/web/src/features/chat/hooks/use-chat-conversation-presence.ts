import { useEffect, useRef } from 'react'

import { postChatConversationPresence } from '../api'

const HEARTBEAT_INTERVAL_MS = 30_000

export function useChatConversationPresence(
  establishmentId: string | null,
  conversationId: string | null,
) {
  const establishmentIdRef = useRef(establishmentId)
  const conversationIdRef = useRef(conversationId)

  useEffect(() => {
    establishmentIdRef.current = establishmentId
    conversationIdRef.current = conversationId
  }, [establishmentId, conversationId])

  useEffect(() => {
    if (!establishmentId || !conversationId) {
      return
    }

    let intervalId: ReturnType<typeof setInterval> | null = null

    const sendPresence = () => {
      const activeEstablishmentId = establishmentIdRef.current
      const activeConversationId = conversationIdRef.current
      if (!activeEstablishmentId || !activeConversationId) {
        return
      }

      void postChatConversationPresence(activeEstablishmentId, activeConversationId).catch(
        () => undefined,
      )
    }

    const startInterval = () => {
      if (intervalId !== null) {
        return
      }
      intervalId = setInterval(sendPresence, HEARTBEAT_INTERVAL_MS)
    }

    const stopInterval = () => {
      if (intervalId === null) {
        return
      }
      clearInterval(intervalId)
      intervalId = null
    }

    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        sendPresence()
        startInterval()
        return
      }
      stopInterval()
    }

    if (document.visibilityState === 'visible') {
      sendPresence()
      startInterval()
    }

    document.addEventListener('visibilitychange', handleVisibilityChange)

    return () => {
      stopInterval()
      document.removeEventListener('visibilitychange', handleVisibilityChange)
    }
  }, [establishmentId, conversationId])
}
