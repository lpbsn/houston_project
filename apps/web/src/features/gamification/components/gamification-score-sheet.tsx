import { Award, Medal, Trophy } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { TerrainBottomSheet } from '@/components/ui/terrain'
import { cn } from '@/lib/utils'

import type { GamificationGradeRule, GamificationPointsRule } from '../types'

type GamificationScoreSheetProps = {
  open: boolean
  onClose: () => void
  pointsRules: GamificationPointsRule[]
  gradeRules: GamificationGradeRule[]
  currentGrade: string | null
}

function formatPoints(rule: GamificationPointsRule) {
  if (rule.points !== null) {
    return `${rule.points > 0 ? '+' : ''}${rule.points} pts`
  }

  if (rule.points_min === rule.points_max) {
    return `${rule.points_min > 0 ? '+' : ''}${rule.points_min} pts`
  }

  return `${rule.points_min} à ${rule.points_max} pts`
}

function gradeIcon(index: number) {
  if (index === 0) {
    return Medal
  }
  if (index === 1) {
    return Award
  }
  return Trophy
}

export function GamificationScoreSheet({
  open,
  onClose,
  pointsRules,
  gradeRules,
  currentGrade,
}: GamificationScoreSheetProps) {
  return (
    <TerrainBottomSheet
      title="Comment fonctionne le score ?"
      open={open}
      onClose={onClose}
      footer={
        <Button
          type="button"
          className="h-11 w-full rounded-full bg-[#114660] font-semibold text-white hover:bg-[#0f3d52]"
          onClick={onClose}
        >
          Compris
        </Button>
      }
    >
      <div className="space-y-5">
        <section className="space-y-2" aria-labelledby="gamification-points-title">
          <h3
            id="gamification-points-title"
            className="text-[10px] font-semibold tracking-[0.06em] text-[#a3a19a] uppercase"
          >
            Points par action
          </h3>
          <ul className="overflow-hidden rounded-[14px] border border-[#E8E6DF] bg-white">
            {pointsRules.map((rule) => (
              <li
                key={rule.code}
                className="flex min-h-10 items-center justify-between gap-3 border-b border-[#E8E6DF] px-3 py-2 last:border-b-0"
              >
                <span className="min-w-0 text-sm text-[#1a1a1a]">{rule.label}</span>
                <span
                  className={cn(
                    'shrink-0 rounded-full px-2 py-1 text-xs font-semibold',
                    rule.points === 0 || (rule.points === null && rule.points_max === 0)
                      ? 'bg-[#F0EFE9] text-[#7D7B75]'
                      : 'bg-[#E8F7F0] text-[#1D9E75]',
                  )}
                >
                  {formatPoints(rule)}
                </span>
              </li>
            ))}
          </ul>
        </section>

        <section className="space-y-2" aria-labelledby="gamification-grades-title">
          <h3
            id="gamification-grades-title"
            className="text-[10px] font-semibold tracking-[0.06em] text-[#a3a19a] uppercase"
          >
            Grades - remise à niveau chaque mois
          </h3>
          <ul className="space-y-2">
            {gradeRules.map((rule, index) => {
              const Icon = gradeIcon(index)
              const isCurrent = currentGrade === rule.code
              return (
                <li
                  key={rule.code}
                  className={cn(
                    'flex min-h-13 items-center gap-3 rounded-[14px] border px-3 py-2.5',
                    isCurrent
                      ? 'border-[#114660] bg-[#114660] text-white'
                      : 'border-[#E8E6DF] bg-white text-[#1a1a1a]',
                  )}
                >
                  <span
                    className={cn(
                      'flex h-8 w-8 shrink-0 items-center justify-center rounded-full',
                      isCurrent ? 'bg-white/15 text-white' : 'bg-[#F5F4F0] text-[#1a1a1a]',
                    )}
                    aria-hidden
                  >
                    <Icon className="h-4 w-4" />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block text-sm font-semibold">{rule.label}</span>
                    <span
                      className={cn(
                        'mt-0.5 block text-xs',
                        isCurrent ? 'text-white/80' : 'text-[#7D7B75]',
                      )}
                    >
                      À partir de {rule.threshold} points
                    </span>
                  </span>
                  {isCurrent ? (
                    <span className="shrink-0 text-[10px] font-bold tracking-[0.06em] uppercase">
                      Débloqué
                    </span>
                  ) : null}
                </li>
              )
            })}
          </ul>
        </section>
      </div>
    </TerrainBottomSheet>
  )
}
