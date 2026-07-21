import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import { CheckCircle2, LoaderCircle } from 'lucide-react'

import { useObservationProcessingBannerView } from '@/features/observations/components/observation-processing-tracker-provider'
import { shouldShowBannerCreatedCheck } from '@/features/observations/lib/observation-processing-banner-state'
import { cn } from '@/lib/utils'

type ObservationProcessingBannerProps = {
  navigate: (pathname: string, options?: { replace?: boolean }) => void
}

export function ObservationProcessingBanner({ navigate }: ObservationProcessingBannerProps) {
  const view = useObservationProcessingBannerView()
  const shouldReduceMotion = useReducedMotion()

  const isInteractive = view.kind === 'terminal' && view.interactive && Boolean(view.navigateTo)
  const showLoader = view.kind === 'progress'
  const showCreatedCheck = shouldShowBannerCreatedCheck(view)
  const label = view.kind === 'hidden' ? null : view.label
  const presenceKey =
    view.kind === 'hidden'
      ? 'hidden'
      : view.kind === 'terminal'
        ? `terminal:${view.observationId}:${view.label}`
        : view.kind === 'progress'
          ? `progress:${view.inProgressCount}:${view.label}`
          : `${view.kind}:${'observationId' in view ? view.observationId : ''}:${view.label}`

  const motionProps = shouldReduceMotion
    ? {
        initial: { opacity: 0 },
        animate: { opacity: 1 },
        exit: { opacity: 0 },
        transition: { duration: 0.15 },
      }
    : {
        initial: { opacity: 0, y: -12 },
        animate: { opacity: 1, y: 0 },
        exit: { opacity: 0, y: -8 },
        transition: { duration: 0.22, ease: 'easeOut' as const },
      }

  return (
    <div className="pointer-events-none absolute inset-x-0 top-0 z-40 px-2 pt-[max(0.5rem,env(safe-area-inset-top))]">
      <AnimatePresence initial={false}>
        {view.kind !== 'hidden' && label ? (
          <motion.div key={presenceKey} className="pointer-events-auto" {...motionProps}>
            <div
              role="status"
              aria-live="polite"
              aria-atomic="true"
              className={cn(
                'flex min-h-12 items-center gap-2 rounded-xl border border-[#E8E6DF] bg-white/95 px-3.5 py-2.5 text-sm text-[#1a1a1a] shadow-[0_8px_24px_rgba(26,26,26,0.12)] backdrop-blur-sm',
                isInteractive ? 'cursor-pointer' : 'cursor-default',
              )}
              tabIndex={isInteractive ? 0 : undefined}
              onClick={() => {
                if (view.kind === 'terminal' && view.navigateTo) {
                  navigate(view.navigateTo)
                }
              }}
              onKeyDown={(event) => {
                if (view.kind !== 'terminal' || !view.navigateTo) {
                  return
                }
                if (event.key === 'Enter' || event.key === ' ') {
                  event.preventDefault()
                  navigate(view.navigateTo)
                }
              }}
            >
              {showLoader ? (
                <LoaderCircle
                  className="h-4 w-4 shrink-0 animate-spin text-[#1B4FD8]"
                  aria-hidden
                />
              ) : null}
              {showCreatedCheck ? (
                <CheckCircle2
                  className="h-5 w-5 shrink-0 text-emerald-700"
                  aria-hidden="true"
                />
              ) : null}
              <p className="min-w-0 flex-1 font-medium leading-snug">{label}</p>
            </div>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </div>
  )
}
