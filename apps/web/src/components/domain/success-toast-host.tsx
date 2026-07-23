import { useSyncExternalStore } from 'react'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import {
  BadgeCheck,
  Ban,
  CheckCircle2,
  CircleCheck,
  Power,
  PowerOff,
  RotateCcw,
  Send,
  Trash2,
  X,
  type LucideIcon,
} from 'lucide-react'

import {
  dismissSuccessToast,
  getSuccessToastsSnapshot,
  subscribeSuccessToasts,
  type SuccessToastKind,
} from '@/lib/success-toast'
import { terrain } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

const KIND_ICONS: Record<SuccessToastKind, LucideIcon> = {
  created: CheckCircle2,
  updated: CircleCheck,
  activated: Power,
  deactivated: PowerOff,
  deleted: Trash2,
  validated: BadgeCheck,
  canceled: Ban,
  reopened: RotateCcw,
  submitted: Send,
  completed: CheckCircle2,
}

function useSuccessToasts() {
  return useSyncExternalStore(subscribeSuccessToasts, getSuccessToastsSnapshot, () => [])
}

export function SuccessToastHost() {
  const toasts = useSuccessToasts()
  const shouldReduceMotion = useReducedMotion()

  const motionProps = shouldReduceMotion
    ? {
        initial: { opacity: 0 },
        animate: { opacity: 1 },
        exit: { opacity: 0 },
        transition: { duration: 0.12 },
      }
    : {
        initial: { opacity: 0, y: 8, scale: 0.98 },
        animate: { opacity: 1, y: 0, scale: 1 },
        exit: { opacity: 0, y: -4, scale: 1 },
        transition: { duration: 0.2, ease: 'easeOut' as const },
      }

  const exitTransition = shouldReduceMotion
    ? { duration: 0.12 }
    : { duration: 0.16, ease: 'easeIn' as const }

  return (
    <div className="flex flex-col gap-2">
      <AnimatePresence initial={false}>
        {toasts.map((toast) => {
          const Icon = KIND_ICONS[toast.kind]
          return (
            <motion.div
              key={toast.id}
              layout={!shouldReduceMotion}
              className="pointer-events-auto"
              {...motionProps}
              exit={{
                ...motionProps.exit,
                transition: exitTransition,
              }}
            >
              <div
                role="status"
                aria-live="polite"
                aria-atomic="true"
                className={cn(
                  'flex min-h-12 items-center gap-2 rounded-xl border bg-white/95 px-3.5 py-2.5 text-sm text-[#1a1a1a] shadow-[0_8px_24px_rgba(26,26,26,0.12)] backdrop-blur-sm',
                  terrain.border,
                )}
              >
                <Icon
                  className={cn('h-5 w-5 shrink-0', terrain.success)}
                  aria-hidden="true"
                  data-toast-kind={toast.kind}
                />
                <p className="min-w-0 flex-1 font-medium leading-snug">{toast.message}</p>
                <button
                  type="button"
                  className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-[#7D7B75] hover:bg-[#F5F4F0] hover:text-[#1a1a1a]"
                  aria-label="Fermer"
                  onClick={() => dismissSuccessToast(toast.id)}
                >
                  <X className="h-4 w-4" aria-hidden="true" />
                </button>
              </div>
            </motion.div>
          )
        })}
      </AnimatePresence>
    </div>
  )
}
