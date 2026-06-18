import houstonLogoSrc from '@/assets/brand/houston-logo-minimal.png'
import { cn } from '@/lib/utils'

type HoustonLogoProps = {
  className?: string
}

export function HoustonLogo({ className }: HoustonLogoProps) {
  return (
    <span className={cn('inline-flex shrink-0', className)}>
      <img
        src={houstonLogoSrc}
        alt="Houston"
        className="h-14 w-auto object-contain"
      />
    </span>
  )
}
