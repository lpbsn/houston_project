import type { ReactNode } from 'react'

type ActionLinkedSignalStripProps = {
  children: ReactNode
}

export function ActionLinkedSignalStrip({ children }: ActionLinkedSignalStripProps) {
  return (
    <div className="shrink-0 border-b border-[#E8E6DF] bg-white px-4 pb-2 pt-1">
      {children}
    </div>
  )
}
