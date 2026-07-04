import { Eye } from 'lucide-react'

import { TerrainCard } from '@/components/ui/terrain'
import { cn } from '@/lib/utils'

type ActionLinkedSignalCardProps = {
  title: string
  locationText: string | null
  onPress?: () => void
}

export function ActionLinkedSignalCard({
  title,
  locationText,
  onPress,
}: ActionLinkedSignalCardProps) {
  const subtitle = locationText?.trim()
    ? `${title} · ${locationText.trim()}`
    : title

  const card = (
    <TerrainCard
      padding="sm"
      className={cn(
        'border-[#D6E4FF] bg-[#EEF4FF]',
        onPress && 'transition-colors group-hover:border-[#B8CCFF] group-hover:bg-[#E4EDFF]',
      )}
    >
      <div className="flex items-start gap-2">
        <div
          className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[#D6E4FF] text-[#1B4FD8]"
          aria-hidden
        >
          <Eye className="h-3.5 w-3.5" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-[10px] font-semibold uppercase tracking-[0.06em] text-[#5B7FD6]">
            Signal lié
          </p>
          <p className="mt-0.5 truncate text-[12px] font-semibold leading-snug text-[#1a1a1a]">
            {subtitle}
          </p>
        </div>
      </div>
    </TerrainCard>
  )

  if (onPress) {
    return (
      <button
        type="button"
        className={cn(
          'group w-full text-left',
          'rounded-[inherit] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1B4FD8]/40',
        )}
        onClick={onPress}
        aria-label="Voir le signal lié"
      >
        {card}
      </button>
    )
  }

  return card
}
