import type { ReactNode } from 'react'

import { TerrainBottomSheet } from '@/components/ui/terrain'

type SignalFeedBottomSheetProps = {
  title: string
  open: boolean
  onClose: () => void
  children: ReactNode
  footer: ReactNode
}

export function SignalFeedBottomSheet({
  title,
  open,
  onClose,
  children,
  footer,
}: SignalFeedBottomSheetProps) {
  return (
    <TerrainBottomSheet title={title} open={open} onClose={onClose} footer={footer}>
      {children}
    </TerrainBottomSheet>
  )
}
