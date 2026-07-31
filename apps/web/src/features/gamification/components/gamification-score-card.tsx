import { useState } from 'react'
import { ChevronRight, Gift, Medal } from 'lucide-react'

import { Button } from '@/components/ui/button'
import {
  HoustonBadge,
  TerrainCard,
  TerrainErrorState,
  TerrainSectionLabel,
} from '@/components/ui/terrain'
import { cn } from '@/lib/utils'

import { GamificationScoreSheet } from './gamification-score-sheet'
import type { GamificationGradeRule, GamificationOverview } from '../types'

type GamificationScoreCardProps = {
  data: GamificationOverview | undefined
  isLoading: boolean
  isError: boolean
  onRetry: () => void
}

function clampProgressRatio(progressRatio: number) {
  return Math.max(0, Math.min(progressRatio, 1))
}

function findGradeLabel(
  grades: GamificationGradeRule[],
  gradeCode: string | null,
): string | null {
  if (!gradeCode) {
    return null
  }

  return grades.find((grade) => grade.code === gradeCode)?.label ?? gradeCode
}

function LoadingScoreCard() {
  return (
    <div className="space-y-2">
      <TerrainSectionLabel>Score & progression</TerrainSectionLabel>
      <TerrainCard className="space-y-3 p-4" aria-busy="true">
        <div className="h-20 animate-pulse rounded-xl bg-[#114660]/15" />
        <div className="h-3 animate-pulse rounded-full bg-[#E8E6DF]" />
        <div className="grid grid-cols-2 gap-2">
          <div className="h-10 animate-pulse rounded-full bg-[#F0EFE9]" />
          <div className="h-10 animate-pulse rounded-full bg-[#F0EFE9]" />
        </div>
      </TerrainCard>
    </div>
  )
}

export function GamificationScoreCard({
  data,
  isLoading,
  isError,
  onRetry,
}: GamificationScoreCardProps) {
  const [isSheetOpen, setIsSheetOpen] = useState(false)

  const current = data?.current
  const gradeRules = data?.rules.grades ?? []
  const pointsRules = data?.rules.points ?? []
  const currentGradeLabel = findGradeLabel(gradeRules, current?.grade ?? null)
  const nextGradeLabel = findGradeLabel(gradeRules, current?.next_grade ?? null)

  if (isLoading) {
    return <LoadingScoreCard />
  }

  if (isError || !current || !data) {
    return (
      <div className="space-y-2">
        <TerrainSectionLabel>Score & progression</TerrainSectionLabel>
        <TerrainErrorState
          message="Le score n'a pas pu être chargé."
          onRetry={onRetry}
        />
      </div>
    )
  }

  const progressRatio = clampProgressRatio(current.progress_ratio)
  const progressPercent = `${progressRatio * 100}%`
  const progressLabel =
    current.is_max_grade || !nextGradeLabel
      ? 'Grade maximal atteint'
      : `Plus que ${current.points_to_next_grade} pts`
  const gradeLabel = currentGradeLabel ?? 'Aucun grade débloqué'

  return (
    <div className="space-y-2">
      <TerrainSectionLabel>Score & progression</TerrainSectionLabel>
      <TerrainCard className="overflow-hidden p-0">
        <div className="flex items-center gap-3 bg-[#114660] px-4 py-4 text-white">
          <span
            className="flex h-14 w-14 shrink-0 items-center justify-center rounded-[18px] border border-white/20 bg-white/15"
            aria-hidden
          >
            <Medal className="h-7 w-7" />
          </span>
          <div className="min-w-0">
            <p className="text-[10px] font-semibold tracking-[0.12em] text-white/70 uppercase">
              Score actuel
            </p>
            <p className="mt-0.5 flex items-end gap-1">
              <span className="text-4xl leading-none font-bold">{current.score}</span>
              <span className="pb-1 text-sm font-semibold text-white/80">pts</span>
            </p>
            <HoustonBadge variant="gray" className="mt-1.5 bg-white/15 text-white">
              {gradeLabel}
            </HoustonBadge>
          </div>
        </div>

        <div className="space-y-3 p-4">
          <div>
            <div className="flex items-end justify-between gap-3">
              <div className="min-w-0">
                <p className="text-[10px] font-semibold tracking-[0.06em] text-[#a3a19a] uppercase">
                  Prochain grade
                </p>
                <p className="truncate text-sm font-semibold text-[#1a1a1a]">
                  {current.is_max_grade || !nextGradeLabel ? 'Grade maximal' : nextGradeLabel}
                </p>
              </div>
              <p className="shrink-0 text-xs font-semibold text-[#7D7B75]">{progressLabel}</p>
            </div>

            <div
              className="mt-3 h-2 overflow-hidden rounded-full bg-[#E8E6DF]"
              role="progressbar"
              aria-valuenow={Math.round(progressRatio * 100)}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label="Progression vers le prochain grade"
            >
              <div
                className="h-full rounded-full bg-linear-to-r from-[#114660] via-[#3A7A96] to-[#7B4DE8]"
                style={{ width: progressPercent }}
              />
            </div>

            <div className="mt-1 flex justify-between text-[10px] text-[#a3a19a]">
              <span>{current.score} pts</span>
              {current.next_grade_threshold !== null ? (
                <span>{current.next_grade_threshold} pts</span>
              ) : null}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <Button
              type="button"
              variant="outline"
              className="h-11 rounded-full border-[#E8E6DF] bg-white text-xs font-semibold text-[#114660]"
              onClick={() => setIsSheetOpen(true)}
            >
              En savoir plus
              <ChevronRight className="h-4 w-4" aria-hidden />
            </Button>
            <Button
              type="button"
              disabled
              aria-label="Récompenses - Bientôt disponible"
              title="Bientôt disponible"
              className={cn(
                'h-11 rounded-full bg-linear-to-r from-[#7B4DE8] to-[#114660] text-xs font-semibold text-white',
                'disabled:opacity-60',
              )}
            >
              <Gift className="h-4 w-4" aria-hidden />
              Récompenses
              <span className="sr-only">Bientôt disponible</span>
            </Button>
          </div>
        </div>
      </TerrainCard>

      <GamificationScoreSheet
        open={isSheetOpen}
        onClose={() => setIsSheetOpen(false)}
        pointsRules={pointsRules}
        gradeRules={gradeRules}
        currentGrade={current.grade}
      />
    </div>
  )
}
