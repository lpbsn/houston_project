import { useMemo, useState } from 'react'
import { ChevronDown, ChevronRight, ChevronUp, Gift, LoaderCircle, Medal } from 'lucide-react'

import { Button } from '@/components/ui/button'
import {
  HoustonBadge,
  TerrainCard,
  TerrainErrorState,
  TerrainSectionLabel,
} from '@/components/ui/terrain'
import { resolveApiErrorMessage } from '@/lib/error-message'
import { cn } from '@/lib/utils'

import { GamificationScoreSheet } from './gamification-score-sheet'
import { GamificationApiError } from '../api'
import { useGamificationTransactionsInfiniteQuery } from '../hooks'
import type {
  GamificationGradeRule,
  GamificationOverview,
  GamificationTransactionItem,
} from '../types'

type GamificationScoreCardProps = {
  establishmentId: string | null
  data: GamificationOverview | undefined
  isLoading: boolean
  isError: boolean
  onRetry: () => void
}

type HistoryDisclosureState = {
  establishmentId: string | null
  isOpen: boolean
  hasOpened: boolean
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

function formatPointDelta(delta: number): string {
  const sign = delta > 0 ? '+' : ''
  const label = Math.abs(delta) === 1 ? 'point' : 'points'
  return `${sign}${delta} ${label}`
}

function formatTransactionDate(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return ''
  }
  return new Intl.DateTimeFormat('fr-FR', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

function uniqueTransactions(items: GamificationTransactionItem[]): GamificationTransactionItem[] {
  const seenIds = new Set<string>()
  const unique: GamificationTransactionItem[] = []

  for (const item of items) {
    if (seenIds.has(item.id)) {
      continue
    }
    seenIds.add(item.id)
    unique.push(item)
  }

  return unique
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
  establishmentId,
  data,
  isLoading,
  isError,
  onRetry,
}: GamificationScoreCardProps) {
  const [isSheetOpen, setIsSheetOpen] = useState(false)
  const [historyState, setHistoryState] = useState<HistoryDisclosureState>({
    establishmentId: null,
    isOpen: false,
    hasOpened: false,
  })

  const historyStateMatchesEstablishment = historyState.establishmentId === establishmentId
  const isHistoryOpen = historyStateMatchesEstablishment ? historyState.isOpen : false
  const hasOpenedHistory = historyStateMatchesEstablishment ? historyState.hasOpened : false
  const transactionsQuery = useGamificationTransactionsInfiniteQuery(
    establishmentId,
    hasOpenedHistory,
  )
  const transactions = useMemo(
    () =>
      uniqueTransactions(transactionsQuery.data?.pages.flatMap((page) => page.items) ?? []),
    [transactionsQuery.data],
  )

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
  const historyContentId = 'gamification-points-history'

  function toggleHistory() {
    setHistoryState((currentState) => {
      const matchesCurrentEstablishment =
        currentState.establishmentId === establishmentId
      const nextIsOpen = matchesCurrentEstablishment ? !currentState.isOpen : true
      return {
        establishmentId,
        isOpen: nextIsOpen,
        hasOpened: matchesCurrentEstablishment
          ? currentState.hasOpened || nextIsOpen
          : nextIsOpen,
      }
    })
  }

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

          <div className="rounded-xl border border-[#E8E6DF] bg-[#F8F7F3]">
            <button
              type="button"
              className="flex min-h-11 w-full items-center justify-between gap-3 px-3 py-2.5 text-left text-sm font-semibold text-[#114660]"
              onClick={toggleHistory}
              aria-expanded={isHistoryOpen}
              aria-controls={historyContentId}
            >
              <span>Historique des points</span>
              {isHistoryOpen ? (
                <ChevronUp className="h-4 w-4 shrink-0 text-[#7D7B75]" aria-hidden />
              ) : (
                <ChevronDown className="h-4 w-4 shrink-0 text-[#7D7B75]" aria-hidden />
              )}
            </button>

            {isHistoryOpen ? (
              <div
                id={historyContentId}
                className="border-t border-[#E8E6DF] px-3 py-3"
              >
                {transactionsQuery.isLoading ? (
                  <div className="flex items-center gap-2 text-sm text-[#7D7B75]">
                    <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden />
                    Chargement de l’historique…
                  </div>
                ) : null}

                {transactionsQuery.isError ? (
                  <div className="space-y-2">
                    <p className="text-sm text-[#7D7B75]">
                      {resolveApiErrorMessage(
                        transactionsQuery.error,
                        GamificationApiError,
                        "L’historique des points n’a pas pu être chargé.",
                      )}
                    </p>
                    <button
                      type="button"
                      className="text-xs font-semibold text-[#1B4FD8]"
                      onClick={() => void transactionsQuery.refetch()}
                    >
                      Réessayer
                    </button>
                  </div>
                ) : null}

                {transactionsQuery.isSuccess && transactions.length === 0 ? (
                  <p className="text-sm text-[#7D7B75]">Aucun point pour le moment.</p>
                ) : null}

                {transactions.length > 0 ? (
                  <div className="space-y-3">
                    <ul className="space-y-2">
                      {transactions.map((transaction) => {
                        const dateLabel = formatTransactionDate(transaction.occurred_at)
                        return (
                          <li
                            key={transaction.id}
                            className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 rounded-lg bg-white px-3 py-2"
                          >
                            <span className="text-sm font-bold text-[#114660]">
                              {formatPointDelta(transaction.delta)}
                            </span>
                            <span className="min-w-0 text-sm font-semibold text-[#1a1a1a]">
                              {transaction.reason_label}
                            </span>
                            {dateLabel ? (
                              <span className="col-start-2 text-xs text-[#7D7B75]">
                                {dateLabel}
                              </span>
                            ) : null}
                          </li>
                        )
                      })}
                    </ul>

                    {transactionsQuery.hasNextPage ? (
                      <div className="flex justify-center pt-1">
                        <button
                          type="button"
                          className="text-xs font-semibold text-[#1B4FD8] disabled:opacity-60"
                          onClick={() => void transactionsQuery.fetchNextPage()}
                          disabled={transactionsQuery.isFetchingNextPage}
                        >
                          {transactionsQuery.isFetchingNextPage
                            ? 'Chargement…'
                            : 'Afficher plus'}
                        </button>
                      </div>
                    ) : (
                      <p className="text-center text-xs text-[#a3a19a]">
                        Fin de l’historique
                      </p>
                    )}
                  </div>
                ) : null}
              </div>
            ) : null}
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
