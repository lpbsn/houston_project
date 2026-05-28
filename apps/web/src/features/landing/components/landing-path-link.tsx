import type { AnchorHTMLAttributes, MouseEvent, PropsWithChildren } from 'react'

type LandingPathLinkProps = PropsWithChildren<{
  className?: string
  href: '/' | '/login'
}> &
  Omit<AnchorHTMLAttributes<HTMLAnchorElement>, 'href'>

export function LandingPathLink({
  children,
  className,
  href,
  onClick,
  ...props
}: LandingPathLinkProps) {
  function handleClick(event: MouseEvent<HTMLAnchorElement>) {
    onClick?.(event)

    if (
      event.defaultPrevented ||
      event.button !== 0 ||
      event.metaKey ||
      event.altKey ||
      event.ctrlKey ||
      event.shiftKey
    ) {
      return
    }

    event.preventDefault()
    window.history.pushState(null, '', href)
    window.dispatchEvent(new PopStateEvent('popstate'))
  }

  return (
    <a href={href} className={className} onClick={handleClick} {...props}>
      {children}
    </a>
  )
}
