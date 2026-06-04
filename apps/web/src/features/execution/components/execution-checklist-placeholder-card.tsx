// PLACEHOLDER — Checklist feed UI preview only; replace when checklist API exists.

import { Check, ClipboardCheck, Clock, MapPin } from 'lucide-react'

import { HoustonBadge } from '@/components/ui/terrain'
import { terrainFeedCardBaseClassName } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

const MOCK = {
  title: 'To do ouverture',
  deadlineLabel: 'avant 10h00',
  completedPoints: 4,
  totalPoints: 12,
  locationLabel: 'Rooftop',
  tasks: [
    { label: 'Températures frigos vérifiées', done: true },
    { label: 'Vérification stock bar', done: false },
    { label: 'Contrôle propreté salle', done: false },
  ],
} as const

const PROGRESS_PERCENT = Math.round((MOCK.completedPoints / MOCK.totalPoints) * 100)

export function ExecutionChecklistPlaceholderCard() {
  return (
    <article
      className={terrainFeedCardBaseClassName(
        'pointer-events-none border border-[#E69138] bg-white',
      )}
      aria-disabled="true"
      aria-label="Checklist — bientôt disponible"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex min-w-0 flex-1 items-center gap-2">
          <ClipboardCheck className="h-4 w-4 shrink-0 text-[#E69138]" aria-hidden />
          <h3 className="truncate text-[15px] font-bold text-[#1a1a1a]">{MOCK.title}</h3>
          <HoustonBadge variant="gray" className="shrink-0 text-[8px]">
            Bientôt
          </HoustonBadge>
        </div>
        <span className="inline-flex shrink-0 items-center gap-1 rounded-full bg-[#FFF9ED] px-2 py-0.5 text-[10px] font-medium text-[#B45309]">
          <Clock className="h-3 w-3" aria-hidden />
          {MOCK.deadlineLabel}
        </span>
      </div>

      <div
        className="mt-3 h-1.5 overflow-hidden rounded-full bg-[#F0EFE9]"
        role="progressbar"
        aria-valuenow={PROGRESS_PERCENT}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="Progression checklist"
      >
        <div
          className="h-full rounded-full bg-[#E69138]"
          style={{ width: `${PROGRESS_PERCENT}%` }}
        />
      </div>

      <div className="mt-2 flex items-center justify-between gap-2 text-[11px] text-[#888]">
        <span>
          {MOCK.completedPoints} / {MOCK.totalPoints} points
        </span>
        <span className="inline-flex shrink-0 items-center gap-1">
          <MapPin className="h-3 w-3 text-[#E24B4A]" aria-hidden />
          {MOCK.locationLabel}
        </span>
      </div>

      <ul className="mt-3 flex flex-col gap-2" aria-hidden>
        {MOCK.tasks.map((task) => (
          <li key={task.label} className="flex items-start gap-2">
            {task.done ? (
              <span
                className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-[4px] bg-[#1D9E75]"
                aria-hidden
              >
                <Check className="h-2.5 w-2.5 text-white" strokeWidth={3} />
              </span>
            ) : (
              <span
                className="mt-0.5 h-4 w-4 shrink-0 rounded-[4px] border border-[#D4D2CB] bg-white"
                aria-hidden
              />
            )}
            <span
              className={cn(
                'text-[13px] leading-snug',
                task.done ? 'text-[#aaa] line-through' : 'text-[#1a1a1a]',
              )}
            >
              {task.label}
            </span>
          </li>
        ))}
      </ul>

      <button
        type="button"
        disabled
        className="mt-4 flex h-10 w-full items-center justify-center rounded-[12px] bg-[#FFF9ED] text-[13px] font-semibold text-[#B45309] disabled:cursor-not-allowed disabled:opacity-70"
      >
        → Continuer
      </button>
    </article>
  )
}
