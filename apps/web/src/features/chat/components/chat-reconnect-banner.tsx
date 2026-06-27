import { terrainStatusBannerClassName } from '@/lib/terrain-styles'

import type { ChatConnectionStatus } from '../types'

type ChatReconnectBannerProps = {
  status: ChatConnectionStatus
}

export function ChatReconnectBanner({ status }: ChatReconnectBannerProps) {
  if (status === 'connected' || status === 'idle') {
    return null
  }

  const label =
    status === 'connecting'
      ? 'Connexion au chat…'
      : status === 'reconnecting'
        ? 'Reconnexion au chat…'
        : 'Chat déconnecté'

  return (
    <div className={terrainStatusBannerClassName()} role="status">
      {label}
    </div>
  )
}
