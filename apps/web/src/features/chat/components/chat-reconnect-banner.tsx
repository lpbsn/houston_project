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
    <div className="border-b border-[#E8E6DF] bg-[#FFF7E8] px-3 py-2 text-center text-xs font-medium text-[#8A5A00]">
      {label}
    </div>
  )
}
