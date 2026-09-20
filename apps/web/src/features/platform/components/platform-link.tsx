import type { MouseEvent, ReactNode } from 'react'

import { useAppRoute } from '@/app/app-routes'
import { shouldHandlePlatformLinkClick } from '@/features/platform/lib/platform-link'
import { cn } from '@/lib/utils'

type PlatformLinkProps = {
  href: string
  children: ReactNode
  className?: string
  'aria-current'?: 'page' | undefined
  'aria-label'?: string
}

export function PlatformLink({
  href,
  children,
  className,
  'aria-current': ariaCurrent,
  'aria-label': ariaLabel,
}: PlatformLinkProps) {
  const { navigate } = useAppRoute()

  return (
    <a
      href={href}
      className={className}
      aria-current={ariaCurrent}
      aria-label={ariaLabel}
      onClick={(event: MouseEvent<HTMLAnchorElement>) => {
        if (!shouldHandlePlatformLinkClick(event)) {
          return
        }
        event.preventDefault()
        navigate(href)
      }}
    >
      {children}
    </a>
  )
}

export function platformNavLinkClass(active: boolean) {
  return cn(
    'relative rounded-lg px-3 py-2 text-sm font-medium',
    active
      ? 'bg-[var(--platform-nav-active)] text-white before:absolute before:inset-y-1.5 before:left-0 before:w-0.5 before:rounded-full before:bg-[var(--platform-accent)]'
      : 'text-[var(--platform-nav-text)] hover:bg-white/5',
  )
}
