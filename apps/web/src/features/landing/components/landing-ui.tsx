import { motion, useReducedMotion } from 'framer-motion'
import type { ReactNode } from 'react'

import { cn } from '@/lib/utils'

type RevealProps = {
  children: ReactNode
  className?: string
  delay?: number
}

export function Reveal({ children, className, delay = 0 }: RevealProps) {
  const reduceMotion = useReducedMotion()

  if (reduceMotion) {
    return <div className={className}>{children}</div>
  }

  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y: 16 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-10% 0px' }}
      transition={{ duration: 0.45, ease: 'easeOut', delay }}
    >
      {children}
    </motion.div>
  )
}

type NeonCtaButtonProps = {
  children: ReactNode
  onClick: () => void
  className?: string
  variant?: 'neon' | 'forest'
}

export function NeonCtaButton({
  children,
  onClick,
  className,
  variant = 'neon',
}: NeonCtaButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'inline-flex items-center justify-center gap-2 rounded-full px-7 py-3.5 text-[15px] font-semibold transition hover:brightness-105 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-3 lg:px-8',
        variant === 'neon' &&
          'landing-cta-glow bg-spore-neon text-spore-forest focus-visible:outline-spore-forest',
        variant === 'forest' &&
          'landing-cta-glow-dark bg-spore-forest text-white focus-visible:outline-spore-neon',
        className,
      )}
    >
      {children}
      <span aria-hidden="true">→</span>
    </button>
  )
}
