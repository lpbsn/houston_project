import { OFFLINE_BANNER_MESSAGE } from '@/lib/network-error'
import { terrainStatusBannerClassName } from '@/lib/terrain-styles'

type NetworkStatusBannerProps = {
  isOnline: boolean
}

export function NetworkStatusBanner({ isOnline }: NetworkStatusBannerProps) {
  if (isOnline) {
    return null
  }

  return (
    <div className={terrainStatusBannerClassName()} role="status">
      {OFFLINE_BANNER_MESSAGE}
    </div>
  )
}
