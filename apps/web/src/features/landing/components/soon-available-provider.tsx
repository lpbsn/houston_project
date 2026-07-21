import { useCallback, useState, type ReactNode } from 'react'

import { SoonAvailableDialog } from '@/features/landing/components/soon-available-dialog'
import { soonAvailableMessages } from '@/features/landing/content'

export type SoonKind = keyof typeof soonAvailableMessages

type SoonAvailableProviderProps = {
  children: (api: { openSoon: (kind: SoonKind) => void }) => ReactNode
}

export function SoonAvailableProvider({ children }: SoonAvailableProviderProps) {
  const [message, setMessage] = useState<string | null>(null)

  const openSoon = useCallback((kind: SoonKind) => {
    setMessage(soonAvailableMessages[kind])
  }, [])

  return (
    <>
      {children({ openSoon })}
      <SoonAvailableDialog
        open={message !== null}
        message={message ?? ''}
        onClose={() => setMessage(null)}
      />
    </>
  )
}
