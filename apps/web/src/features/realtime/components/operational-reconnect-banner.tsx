import { terrainStatusBannerClassName } from '@/lib/terrain-styles'

import type { OperationalRealtimeConnectionStatus } from '../types'

type OperationalReconnectBannerProps = {
  status: OperationalRealtimeConnectionStatus
}

export function OperationalReconnectBanner({ status }: OperationalReconnectBannerProps) {
  if (status !== 'reconnecting' && status !== 'disconnected') {
    return null
  }

  const label =
    status === 'reconnecting' ? 'Reconnexion en cours…' : 'Connexion perdue'

  return (
    <div className={terrainStatusBannerClassName()} role="status">
      {label}
    </div>
  )
}
