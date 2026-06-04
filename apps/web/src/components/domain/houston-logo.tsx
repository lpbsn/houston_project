import houstonLogoSrc from '@/assets/brand/houston-logo.png'
import { cn } from '@/lib/utils'

type HoustonLogoProps = {
  className?: string
}

export function HoustonLogo({ className }: HoustonLogoProps) {
  return (
    <span
      className={cn(
        'inline-flex size-30 shrink-0 overflow-hidden rounded-full',
        className,
      )}
    >
      <img
        src={houstonLogoSrc}
        alt="Houston"
        className="size-full scale-[1.08] object-cover"
      />
    </span>
  )
}
