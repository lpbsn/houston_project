import { useMemo, useState, type ReactNode } from 'react'
import { ArrowDownRight, ArrowUpRight, Download, Info } from 'lucide-react'
import { Popover } from 'radix-ui'

import type {
  AnalyticsContributorItem,
  AnalyticsDashboardMetricComparison,
  AnalyticsDashboardResponse,
  AnalyticsNamedCountItem,
  AnalyticsNewPatternItem,
  AnalyticsRecurringPatternItem,
} from '@/features/analytics/api'
import { useAnalyticsDashboardRankingsInfiniteQuery } from '@/features/analytics/hooks'
import {
  canShowDashboardDelta,
  contributorInitials,
  dashboardNewBadgeTone,
  dashboardNewLabel,
  dashboardTrendTone,
  emptyDeadlineRespectMessage,
  emptyOverrunMessage,
  emptyResolutionQualityMessage,
  formatAbsentPreviousPeriodLabel,
  formatContributorPoles,
  formatDashboardCountDelta,
  formatDashboardDuration,
  formatDashboardDurationDelta,
  formatDashboardPercent,
  formatDashboardPercentDelta,
  formatDashboardPointsDelta,
  formatDeadlineAnalyzedTotal,
  formatDeadlineExclusionNote,
  formatOverrunBucketStat,
  formatOverrunExclusionNote,
  formatOverrunTotal,
  formatRelativeDaysAgo,
  formatResolutionQualityTotal,
  formatUnevaluatedPlansNote,
  type DashboardTrendSense,
} from '@/features/analytics/lib/dashboard-comparisons'
import {
  assignPoleColors,
  destinationChartColor,
  poleChartColor,
} from '@/features/analytics/lib/dashboard-chart-colors'
import {
  barHeightPercent,
  integerYAxis,
  VOLUME_PLOT_HEIGHT_PX,
  volumeSegmentLabelVisible,
} from '@/features/analytics/lib/dashboard-chart-scale'
import type { DashboardPeriodDays } from '@/features/analytics/lib/dashboard-url-state'
import { cn } from '@/lib/utils'

const VOLUME_LABEL_LINES: Record<string, readonly [string, string]> = {
  four_periods_ago: ['Il y a 4', 'périodes'],
  three_periods_ago: ['Il y a 3', 'périodes'],
  two_periods_ago: ['Il y a 2', 'périodes'],
  previous: ['Période', 'précédente'],
  current: ['Période', 'en cours'],
}

const DESTINATION_LABELS: Record<string, string> = {
  waiting: 'En attente',
  interesting: 'Intéressante',
  action_plan_in_progress: 'Plan d’action en cours',
  resolved_direct: 'Résolue directement',
  resolved_via_action_plan: 'Résolue via un plan d’action',
  resolved_via_resolution_request: 'Résolue après demande de résolution',
  canceled: 'Annulée',
}


const DELAY_ORDER = [
  'interesting',
  'action_plan_in_progress',
  'resolved_direct',
  'resolved_via_action_plan',
  'resolved_via_resolution_request',
  'canceled',
] as const

const OVERRUN_LABELS: Record<string, string> = {
  lt_10: 'moins de 10 % de dépassement',
  from_10_to_25: 'de 10 % à moins de 25 %',
  from_25_to_50: 'de 25 % à moins de 50 %',
  from_50_to_100: 'de 50 % à moins de 100 %',
  gte_100: '100 % de dépassement ou plus',
}

function DashboardCard({
  title,
  subtitle,
  children,
  titleTooltip,
  titleTooltipAriaLabel,
}: {
  title: string
  subtitle?: string
  children: ReactNode
  titleTooltip?: string
  titleTooltipAriaLabel?: string
}) {
  return (
    <section className="flex min-w-0 flex-col rounded-2xl border border-[#E8E6DF] bg-white p-5 lg:p-6">
      <div>
        <div className="flex min-w-0 items-center gap-1.5">
          <h2 className="text-base font-semibold tracking-tight text-[#1a1a1a]">{title}</h2>
          {titleTooltip && titleTooltipAriaLabel ? (
            <Popover.Root>
              <Popover.Trigger
                aria-label={titleTooltipAriaLabel}
                className="inline-flex shrink-0 rounded-md text-[#7D7B75] outline-none focus-visible:ring-2 focus-visible:ring-[#1a1a1a]/20"
              >
                <Info className="h-4 w-4" aria-hidden />
              </Popover.Trigger>
              <Popover.Portal>
                <Popover.Content
                  align="start"
                  side="bottom"
                  sideOffset={6}
                  className="z-50 max-w-sm rounded-xl border border-[#E8E6DF] bg-white p-3 text-sm leading-relaxed text-[#1a1a1a] shadow-sm outline-none"
                >
                  {titleTooltip}
                </Popover.Content>
              </Popover.Portal>
            </Popover.Root>
          ) : null}
        </div>
        {subtitle ? <p className="mt-1 text-[12px] text-[#7D7B75]">{subtitle}</p> : null}
      </div>
      <div className="mt-4 min-w-0">{children}</div>
    </section>
  )
}

function isDisplayedTrendFlat(
  delta: number | null,
  format: 'percent' | 'points' | 'count' | 'duration',
): boolean {
  if (delta == null) {
    return false
  }
  if (format === 'percent' || format === 'points') {
    return Math.round(Math.abs(delta) * 100) === 0
  }
  return delta === 0
}

export function TrendBadge({
  comparison,
  sense,
  format = 'percent',
  periodDays,
}: {
  comparison: AnalyticsDashboardMetricComparison
  sense: DashboardTrendSense
  format?: 'percent' | 'points' | 'count' | 'duration'
  periodDays: number
}) {
  if (!canShowDashboardDelta(comparison)) {
    return null
  }
  if (dashboardNewLabel(comparison)) {
    const newTone = dashboardNewBadgeTone(sense)
    return (
      <span
        className={cn(
          'text-[12px] font-semibold',
          newTone === 'neutral' ? 'text-[#7D7B75]' : 'text-[#1F7A4D]',
        )}
      >
        {formatAbsentPreviousPeriodLabel(periodDays)}
      </span>
    )
  }
  const delta =
    format === 'points' || format === 'count' || format === 'duration'
      ? comparison.absolute_delta
      : comparison.relative_change
  const label =
    format === 'points'
      ? formatDashboardPointsDelta(comparison.relative_change, periodDays)
      : format === 'count'
        ? formatDashboardCountDelta(comparison.absolute_delta)
        : format === 'duration'
          ? formatDashboardDurationDelta(comparison.absolute_delta, periodDays)
          : formatDashboardPercentDelta(comparison.relative_change)
  if (!label || isDisplayedTrendFlat(delta, format)) {
    return null
  }
  const tone = dashboardTrendTone(delta, sense)
  const Icon = (delta ?? 0) < 0 ? ArrowDownRight : ArrowUpRight
  return (
    <span
      className={cn(
        'inline-flex min-w-0 flex-wrap items-center gap-0.5 text-[12px] font-semibold',
        tone === 'positive' && 'text-[#1F7A4D]',
        tone === 'negative' && 'text-[#E24B4A]',
        tone === 'neutral' && 'text-[#7D7B75]',
      )}
    >
      <Icon className="h-3.5 w-3.5" aria-hidden />
      {label}
    </span>
  )
}

export function DashboardExportButton() {
  return (
    <button
      type="button"
      disabled
      className="inline-flex h-9 min-w-0 items-center gap-2 rounded-lg bg-[#1F7A4D] px-3.5 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-70"
    >
      <Download className="h-4 w-4" aria-hidden />
      Exporter
    </button>
  )
}

export function DashboardFilterPlaceholders() {
  return (
    <div className="grid min-w-0 gap-3 rounded-2xl border border-[#E8E6DF] bg-white p-3 lg:grid-cols-3">
      {(
        [
          ['Pôles d’activités', 'Tous les pôles'],
          ['Sujets', 'Tous les sujets'],
          ['Responsable', 'Tous les responsables'],
        ] as const
      ).map(([label, value]) => (
        <label key={label} className="min-w-0">
          <span className="mb-1.5 block text-[11px] font-semibold tracking-[0.06em] text-[#7D7B75] uppercase">
            {label}
          </span>
          <div className="flex h-11 items-center justify-between rounded-xl border border-[#E8E6DF] px-3 text-sm text-[#7D7B75]">
            <span>{value}</span>
            <span aria-hidden>▾</span>
          </div>
        </label>
      ))}
    </div>
  )
}

function AiPlaceholder() {
  return (
    <div className="mt-4 rounded-xl bg-[#F5F4F0] px-4 py-3">
      <p className="text-[11px] font-semibold tracking-[0.08em] text-[#1F7A4D] uppercase">
        Impact futur potentiel · IA
      </p>
      <p className="mt-1 text-[13px] text-[#7D7B75]">Bientôt disponible</p>
    </div>
  )
}

function RankingOverlay({
  title,
  children,
  onClose,
}: {
  title: string
  children: ReactNode
  onClose: () => void
}) {
  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/40" role="dialog" aria-modal>
      <div className="flex h-full w-full max-w-lg flex-col bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-[#E8E6DF] px-5 py-4">
          <h2 className="text-base font-semibold">{title}</h2>
          <button type="button" className="text-sm text-[#7D7B75]" onClick={onClose}>
            Fermer
          </button>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4">{children}</div>
      </div>
    </div>
  )
}

function SeeAllButton({
  visible,
  onClick,
}: {
  visible: boolean
  onClick: () => void
}) {
  if (!visible) {
    return null
  }
  return (
    <button type="button" onClick={onClick} className="mt-3 text-sm font-semibold text-[#1F7A4D]">
      Voir tout
    </button>
  )
}

export function RecurringPatternsCard({
  preview,
  establishmentId,
  periodDays,
}: {
  preview: AnalyticsDashboardResponse['recurring_patterns']
  establishmentId: string
  periodDays: DashboardPeriodDays
}) {
  const [open, setOpen] = useState(false)
  return (
    <DashboardCard title="Sujets récurrents">
      <RecurringList items={preview.items} periodDays={periodDays} />
      <SeeAllButton visible={preview.total_count > preview.items.length} onClick={() => setOpen(true)} />
      <AiPlaceholder />
      {open ? (
        <RankingOverlay title="Sujets récurrents" onClose={() => setOpen(false)}>
          <RankingPages
            kind="recurring"
            establishmentId={establishmentId}
            periodDays={periodDays}
            renderItem={(item) => {
              const row = item as AnalyticsRecurringPatternItem
              return (
                <RecurringRow
                  key={row.pattern_id}
                  item={row}
                  periodDays={periodDays}
                />
              )
            }}
          />
        </RankingOverlay>
      ) : null}
    </DashboardCard>
  )
}

function RecurringList({
  items,
  periodDays,
}: {
  items: AnalyticsRecurringPatternItem[]
  periodDays: number
}) {
  if (items.length === 0) {
    return <p className="text-sm text-[#7D7B75]">Aucun sujet récurrent sur cette période.</p>
  }
  return (
    <ul className="flex flex-col gap-3">
      {items.map((item) => (
        <RecurringRow key={item.pattern_id} item={item} periodDays={periodDays} />
      ))}
    </ul>
  )
}

function RecurringRow({
  item,
  periodDays,
}: {
  item: AnalyticsRecurringPatternItem
  periodDays: number
}) {
  return (
    <li className="flex min-w-0 items-start justify-between gap-3">
      <div className="min-w-0">
        <p className="truncate text-sm font-medium text-[#1a1a1a]">{item.name}</p>
      </div>
      <div className="flex shrink-0 items-center gap-2">
        <span className="tabular-nums text-sm font-semibold">{item.signal_count}</span>
        <TrendBadge comparison={item.comparison} sense="neutral" format="count" periodDays={periodDays} />
      </div>
    </li>
  )
}

export function NewPatternsCard({
  preview,
  establishmentId,
  periodDays,
}: {
  preview: AnalyticsDashboardResponse['new_patterns']
  establishmentId: string
  periodDays: DashboardPeriodDays
}) {
  const [open, setOpen] = useState(false)
  return (
    <DashboardCard title="Nouveaux sujets">
      {preview.items.length === 0 ? (
        <p className="text-sm text-[#7D7B75]">Aucun nouveau sujet sur cette période.</p>
      ) : (
        <ul className="flex flex-col gap-3">
          {preview.items.map((item) => (
            <NewRow key={item.pattern_id} item={item} />
          ))}
        </ul>
      )}
      <SeeAllButton visible={preview.total_count > preview.items.length} onClick={() => setOpen(true)} />
      <AiPlaceholder />
      {open ? (
        <RankingOverlay title="Nouveaux sujets" onClose={() => setOpen(false)}>
          <RankingPages
            kind="new"
            establishmentId={establishmentId}
            periodDays={periodDays}
            renderItem={(item) => <NewRow key={(item as AnalyticsNewPatternItem).pattern_id} item={item as AnalyticsNewPatternItem} />}
          />
        </RankingOverlay>
      ) : null}
    </DashboardCard>
  )
}

function NewRow({ item }: { item: AnalyticsNewPatternItem }) {
  return (
    <li className="min-w-0">
      <p className="truncate text-sm font-medium text-[#1a1a1a]">{item.name}</p>
      <p className="text-[12px] text-[#7D7B75]">{formatRelativeDaysAgo(item.first_seen_at)}</p>
    </li>
  )
}

export function ObservationVolumeCard({
  volume,
  periodDays,
}: {
  volume: AnalyticsDashboardResponse['observation_volume']
  periodDays: number
}) {
  const [mode, setMode] = useState<'affected' | 'responsible'>('responsible')
  const selected = volume[mode]
  const poleColors = useMemo(() => assignPoleColors(selected.windows), [selected.windows])
  const maxTotal = Math.max(...selected.windows.map((window) => window.total), 0)
  const { scaleMax, ticks } = integerYAxis(maxTotal)
  const legend = useMemo(
    () =>
      Array.from(
        new Map(
          selected.windows.flatMap((window) =>
            window.segments.map((segment) => [segment.pole_id, segment.name] as const),
          ),
        ),
      ),
    [selected.windows],
  )

  return (
    <DashboardCard title="Nombre d’observations">
      <div
        className="mb-4 inline-flex rounded-lg bg-[#F5F4F0] p-1"
        data-volume-mode={mode}
      >
        <button
          type="button"
          aria-pressed={mode === 'responsible'}
          data-volume-mode-option="responsible"
          onClick={() => setMode('responsible')}
          className={cn(
            'rounded-md px-3 py-1.5 text-[12px] font-semibold',
            mode === 'responsible' ? 'bg-white text-[#1a1a1a] shadow-sm' : 'text-[#7D7B75]',
          )}
        >
          Pôle responsable
        </button>
        <button
          type="button"
          aria-pressed={mode === 'affected'}
          data-volume-mode-option="affected"
          onClick={() => setMode('affected')}
          className={cn(
            'rounded-md px-3 py-1.5 text-[12px] font-semibold',
            mode === 'affected' ? 'bg-white text-[#1a1a1a] shadow-sm' : 'text-[#7D7B75]',
          )}
        >
          Pôle concerné
        </button>
      </div>
      <div className="min-w-0">
        <div className="grid grid-cols-[2.5rem_minmax(0,1fr)] gap-x-1">
          <div />
          <div className="grid grid-cols-5 gap-1">
            {selected.windows.map((window) => (
              <p
                key={`${window.label_key}-total`}
                className="mb-1 text-center text-sm font-semibold tabular-nums sm:text-lg"
              >
                {window.total}
              </p>
            ))}
          </div>
          <div className="relative" style={{ height: VOLUME_PLOT_HEIGHT_PX }}>
            {ticks.map((tick) => (
              <span
                key={tick}
                className="absolute right-0 -translate-y-1/2 text-[10px] leading-none text-[#7D7B75] tabular-nums"
                style={{ bottom: scaleMax === 0 ? '0%' : `${barHeightPercent(tick, scaleMax)}%` }}
              >
                {tick}
              </span>
            ))}
          </div>
          <div className="relative min-w-0" style={{ height: VOLUME_PLOT_HEIGHT_PX }}>
            {ticks.map((tick) => (
              <div
                key={tick}
                className="absolute inset-x-0 border-t border-[#E8E6DF]"
                style={{
                  bottom:
                    scaleMax === 0
                      ? '0%'
                      : `${barHeightPercent(tick, scaleMax)}%`,
                }}
              />
            ))}
            <div className="relative z-[1] grid h-full grid-cols-5 items-end gap-1.5 sm:gap-3">
              {selected.windows.map((window) => (
                <div
                  key={window.label_key}
                  data-volume-window={window.label_key}
                  className="flex h-full min-w-0 w-full flex-col items-center justify-end"
                >
                  <div
                    className="flex w-[55%] min-w-0 flex-col-reverse overflow-hidden rounded-md"
                    style={{
                      height: scaleMax === 0 ? 0 : `${barHeightPercent(window.total, scaleMax)}%`,
                    }}
                  >
                    {window.segments.map((segment) => {
                      const showLabel = volumeSegmentLabelVisible(
                        segment.count,
                        scaleMax,
                        VOLUME_PLOT_HEIGHT_PX,
                      )
                      return (
                        <span
                          key={segment.pole_id}
                          data-pole-id={segment.pole_id}
                          className="flex min-h-0 w-full items-center justify-center px-0.5 text-center text-[10px] leading-tight font-semibold text-white sm:text-[11px]"
                          style={{
                            height:
                              window.total === 0
                                ? '0%'
                                : `${(segment.count / window.total) * 100}%`,
                            backgroundColor: poleChartColor(segment.pole_id, poleColors),
                          }}
                        >
                          {showLabel
                            ? `${segment.count} (${formatDashboardPercent(segment.share)})`
                            : null}
                        </span>
                      )
                    })}
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div />
          <div className="mt-2 grid grid-cols-5 gap-1">
            {selected.windows.map((window) => {
              const lines = VOLUME_LABEL_LINES[window.label_key]
              return (
                <p
                  key={`${window.label_key}-label`}
                  className={cn(
                    'text-center text-[10px] leading-tight text-[#7D7B75] sm:text-[11px]',
                    window.label_key === 'current' && 'font-semibold text-[#1a1a1a]',
                  )}
                >
                  {lines ? (
                    <>
                      {lines[0]}
                      <br />
                      {lines[1]}
                    </>
                  ) : (
                    window.label_key
                  )}
                </p>
              )
            })}
          </div>
        </div>
      </div>
      <div className="mt-4 flex flex-wrap gap-3 text-[12px] text-[#7D7B75]">
        {legend.map(([poleId, name]) => (
          <span key={poleId} className="inline-flex items-center gap-1.5">
            <span
              className="h-2.5 w-2.5 rounded-sm"
              data-legend-pole-id={poleId}
              style={{ backgroundColor: poleChartColor(poleId, poleColors) }}
            />
            {name}
          </span>
        ))}
      </div>
      <div className="mt-4 flex items-end justify-between border-t border-[#E8E6DF] pt-3">
        <div>
          <p className="text-[12px] text-[#7D7B75]">Total période</p>
          <p className="text-2xl font-semibold tabular-nums">{selected.current_total}</p>
        </div>
        <TrendBadge
          comparison={selected.comparison}
          sense="positive-up"
          format="count"
          periodDays={periodDays}
        />
      </div>
    </DashboardCard>
  )
}

export function ObservationDestinationsCard({
  destinations,
  periodDays,
}: {
  destinations: AnalyticsDashboardResponse['observation_destinations']
  periodDays: number
}) {
  const keys = Object.keys(DESTINATION_LABELS)
  const [selectedKey, setSelectedKey] = useState<string | null>(null)
  const selectedLabel = selectedKey ? DESTINATION_LABELS[selectedKey] : null
  const selectedItem = selectedKey ? destinations[selectedKey] : null

  return (
    <DashboardCard title="Destination des observations">
      <div className="flex h-3.5 overflow-hidden rounded-full bg-[#F0EFE9]">
        {keys.map((key) => {
          const share = destinations[key]?.share ?? 0
          if (share <= 0) {
            return null
          }
          const color = destinationChartColor(key)
          return (
            <button
              key={key}
              type="button"
              aria-pressed={selectedKey === key}
              aria-label={`${DESTINATION_LABELS[key]} ${formatDashboardPercent(share)}`}
              className="h-full min-w-0 p-0"
              style={{ width: `${share * 100}%`, backgroundColor: color }}
              onClick={() => setSelectedKey((current) => (current === key ? null : key))}
              onKeyDown={(event) => {
                if (event.key === 'Escape') {
                  setSelectedKey(null)
                }
              }}
            />
          )
        })}
      </div>
      {selectedLabel && selectedItem ? (
        <p className="mt-2 text-[12px] text-[#7D7B75]">
          <span
            className="mr-1.5 inline-block h-2.5 w-2.5 rounded-sm align-middle"
            style={{ backgroundColor: destinationChartColor(selectedKey) }}
          />
          {selectedLabel} · {formatDashboardPercent(selectedItem.share)}
        </p>
      ) : null}
      <ul className="mt-4 flex flex-col gap-2">
        {keys.map((key) => {
          const item = destinations[key]
          if (!item) {
            return null
          }
          const color = destinationChartColor(key)
          return (
            <li key={key} className="flex items-center justify-between gap-3 text-sm">
              <span className="inline-flex items-center gap-2 text-[#7D7B75]">
                <span
                  className="h-2.5 w-2.5 rounded-sm"
                  data-destination-swatch={key}
                  style={{ backgroundColor: color }}
                />
                {DESTINATION_LABELS[key]}
              </span>
              <span className="flex items-center gap-2">
                <span className="tabular-nums font-medium text-[#1a1a1a]">
                  {formatDashboardPercent(item.share)}
                </span>
                <TrendBadge
                  comparison={item.comparison}
                  sense="neutral"
                  format="percent"
                  periodDays={periodDays}
                />
              </span>
            </li>
          )
        })}
      </ul>
      <p className="mt-3 text-[11px] tracking-[0.08em] text-[#7D7B75] uppercase">
        vs période précédente
      </p>
    </DashboardCard>
  )
}

export function ObservationDestinationDelaysCard({
  delays,
}: {
  delays: AnalyticsDashboardResponse['observation_destination_delays']
}) {
  const max = Math.max(
    ...DELAY_ORDER.map((key) => delays[key]?.mean_seconds ?? 0),
    1,
  )
  return (
    <DashboardCard
      title="Délai avant chaque destination"
      subtitle="Délai moyen entre l’observation et sa destination"
    >
      <ul className="flex flex-col gap-3">
        {DELAY_ORDER.map((key) => {
          const item = delays[key]
          const value = item?.mean_seconds ?? null
          return (
            <li key={key} className="min-w-0">
              <div className="mb-1 flex items-center justify-between gap-3 text-sm">
                <span className="text-[#1a1a1a]">{DESTINATION_LABELS[key]}</span>
                <span className="tabular-nums font-medium">
                  {item && item.n > 0 ? formatDashboardDuration(value) : '—'}
                </span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-[#F0EFE9]">
                {value != null && item && item.n > 0 ? (
                  <span
                    className="block h-full rounded-full bg-[#1F7A4D]"
                    style={{ width: `${(value / max) * 100}%` }}
                  />
                ) : null}
              </div>
            </li>
          )
        })}
      </ul>
    </DashboardCard>
  )
}

export function PlanDeadlineRespectCard({
  data,
  periodDays,
}: {
  data: AnalyticsDashboardResponse['plan_deadline_respect']
  periodDays: number
}) {
  const exclusionNote = formatDeadlineExclusionNote(data.excluded_count)
  const isEmpty = data.n === 0 && data.excluded_count === 0
  return (
    <DashboardCard title="Respect des échéances des plans d’action">
      {isEmpty ? (
        <p className="text-sm text-[#7D7B75]">{emptyDeadlineRespectMessage()}</p>
      ) : (
        <>
          <p className="text-sm text-[#7D7B75] tabular-nums">{formatDeadlineAnalyzedTotal(data.n)}</p>
          {data.n > 0 ? (
            <>
              <div className="mt-4 flex h-6 overflow-hidden rounded-full bg-[#F0EFE9]">
                {data.early ? (
                  <span className="bg-[#1F7A4D]" style={{ width: `${data.early * 100}%` }} />
                ) : null}
                {data.on_time ? (
                  <span className="bg-[#111111]" style={{ width: `${data.on_time * 100}%` }} />
                ) : null}
                {data.late ? (
                  <span className="bg-[#E24B4A]" style={{ width: `${data.late * 100}%` }} />
                ) : null}
              </div>
              <div className="mt-4 grid gap-4 sm:grid-cols-3">
                {(
                  [
                    ['Terminé en avance', data.early, data.early_comparison, 'positive-up'],
                    ['Terminé à temps', data.on_time, data.on_time_comparison, 'positive-up'],
                    ['Terminé en retard', data.late, data.late_comparison, 'negative-up'],
                  ] as const
                ).map(([label, share, comparison, sense]) => (
                  <div key={label}>
                    <p className="text-[12px] text-[#7D7B75]">{label}</p>
                    <p className="text-lg font-semibold tabular-nums">{formatDashboardPercent(share)}</p>
                    <TrendBadge
                      comparison={comparison}
                      sense={sense}
                      format="percent"
                      periodDays={periodDays}
                    />
                  </div>
                ))}
              </div>
            </>
          ) : null}
          {exclusionNote ? <p className="mt-3 text-[12px] text-[#7D7B75]">{exclusionNote}</p> : null}
        </>
      )}
    </DashboardCard>
  )
}

export function PlanOverrunCard({
  data,
}: {
  data: AnalyticsDashboardResponse['plan_overrun']
}) {
  const exclusionNote = formatOverrunExclusionNote(data.excluded_count)
  const max = Math.max(...data.buckets.map((bucket) => bucket.count), 1)
  return (
    <DashboardCard
      title="Plans d’action en retard"
      titleTooltip="Le taux de dépassement compare le temps de retard à la durée planifiée du plan. Plus le pourcentage est élevé, plus le retard est important par rapport au délai prévu. Exemple : 2 jours de retard sur un plan de 30 jours représentent 6,7 %, tandis que 2 jours de retard sur un plan de 2 jours représentent 100 %."
      titleTooltipAriaLabel="Informations sur le taux de dépassement"
    >
      {data.total_count === 0 ? (
        <p className="text-sm text-[#7D7B75]">{emptyOverrunMessage()}</p>
      ) : (
        <>
          <p className="text-sm tabular-nums text-[#7D7B75]">{formatOverrunTotal(data.total_count)}</p>
          {data.analyzed_count > 0 ? (
            <ul className="mt-4 flex flex-col gap-2">
              {data.buckets.map((bucket) => (
                <li key={bucket.key} className="rounded-xl bg-[#F5F4F0] px-3 py-2">
                  <div className="flex items-center justify-between gap-3 text-sm">
                    <span>{OVERRUN_LABELS[bucket.key] ?? bucket.key}</span>
                    <span className="tabular-nums text-[#7D7B75]">
                      {formatOverrunBucketStat(bucket.count, bucket.share)}
                    </span>
                  </div>
                  <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-white">
                    <span
                      className="block h-full bg-[#111111]"
                      style={{ width: `${(bucket.count / max) * 100}%` }}
                    />
                  </div>
                </li>
              ))}
            </ul>
          ) : null}
          {exclusionNote ? <p className="mt-3 text-[12px] text-[#7D7B75]">{exclusionNote}</p> : null}
        </>
      )}
    </DashboardCard>
  )
}

function StarRow({ filled }: { filled: number }) {
  const label = filled === 0 ? '0 étoile' : `${filled} étoile${filled > 1 ? 's' : ''}`
  return (
    <span role="img" aria-label={label} className="inline-flex items-center text-[#1F7A4D]">
      <span className="inline-flex gap-0.5">
        {Array.from({ length: 5 }, (_, index) => (
          <span key={index}>{index < filled ? '★' : '☆'}</span>
        ))}
      </span>
    </span>
  )
}

export function ResolutionQualityCard({
  data,
}: {
  data: AnalyticsDashboardResponse['resolution_quality']
}) {
  const unevaluatedNote = formatUnevaluatedPlansNote(data.unevaluated_count)
  const max = Math.max(...data.buckets.map((bucket) => bucket.share ?? 0), 0.01)
  return (
    <DashboardCard title="Qualité des résolutions de plans d’action">
      {data.n === 0 ? (
        <p className="text-sm text-[#7D7B75]">{emptyResolutionQualityMessage()}</p>
      ) : (
        <>
          <p className="text-sm text-[#7D7B75] tabular-nums">{formatResolutionQualityTotal(data.n)}</p>
          {unevaluatedNote ? (
            <p className="mt-2 text-[12px] text-[#7D7B75]">{unevaluatedNote}</p>
          ) : null}
          <ul className="mt-4 flex flex-col gap-2">
            {data.buckets.map((bucket) => (
              <li key={bucket.stars} className="flex items-center gap-3">
                <StarRow filled={bucket.stars} />
                <div className="h-2 min-w-0 flex-1 overflow-hidden rounded-full bg-[#F0EFE9]">
                  {bucket.share != null ? (
                    <span
                      className="block h-full bg-[#1F7A4D]"
                      style={{ width: `${(bucket.share / max) * 100}%` }}
                    />
                  ) : null}
                </div>
                <span className="w-10 text-right text-sm tabular-nums">
                  {formatDashboardPercent(bucket.share)}
                </span>
              </li>
            ))}
          </ul>
        </>
      )}
    </DashboardCard>
  )
}

export function ContributorsCard({
  items,
}: {
  items: AnalyticsContributorItem[]
}) {
  return (
    <DashboardCard title="Classement des contributeurs">
      {items.length === 0 ? (
        <p className="text-sm text-[#7D7B75]">Aucun contributeur sur cette période.</p>
      ) : (
        <ol className="flex flex-col gap-3">
          {items.map((item, index) => (
            <li key={item.user_id} className="flex items-center justify-between gap-3">
              <div className="flex min-w-0 items-center gap-3">
                <span className="w-4 text-sm text-[#7D7B75]">{index + 1}</span>
                <span className="flex h-8 w-8 items-center justify-center rounded-full bg-[#F0EFE9] text-[11px] font-semibold">
                  {contributorInitials(item.name)}
                </span>
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">{item.name}</p>
                  <p className="truncate text-[12px] text-[#7D7B75]">{formatContributorPoles(item.poles)}</p>
                </div>
              </div>
              <span className="shrink-0 text-sm font-semibold text-[#1F7A4D] tabular-nums">
                {new Intl.NumberFormat('fr-FR').format(item.pts)} pts
              </span>
            </li>
          ))}
        </ol>
      )}
    </DashboardCard>
  )
}

export function LocationsCard({
  preview,
  establishmentId,
  periodDays,
}: {
  preview: AnalyticsDashboardResponse['locations']
  establishmentId: string
  periodDays: DashboardPeriodDays
}) {
  const [open, setOpen] = useState(false)
  const max = Math.max(...preview.items.map((item) => item.count), 1)
  return (
    <DashboardCard title="Lieux les plus cités">
      {preview.items.length === 0 ? (
        <p className="text-sm text-[#7D7B75]">Aucun lieu cité sur cette période.</p>
      ) : (
        <LocationList items={preview.items} max={max} />
      )}
      <SeeAllButton visible={preview.total_count > preview.items.length} onClick={() => setOpen(true)} />
      {open ? (
        <RankingOverlay title="Lieux les plus cités" onClose={() => setOpen(false)}>
          <RankingPages
            kind="locations"
            establishmentId={establishmentId}
            periodDays={periodDays}
            renderItem={(item) => {
              const location = item as AnalyticsNamedCountItem
              return <LocationRow key={location.id} item={location} max={max} />
            }}
          />
        </RankingOverlay>
      ) : null}
    </DashboardCard>
  )
}

function LocationList({
  items,
  max,
}: {
  items: AnalyticsNamedCountItem[]
  max: number
}) {
  return (
    <ul className="flex flex-col gap-3">
      {items.map((item) => (
        <LocationRow key={item.id} item={item} max={max} />
      ))}
    </ul>
  )
}

function LocationRow({ item, max }: { item: AnalyticsNamedCountItem; max: number }) {
  return (
    <li>
      <div className="mb-1 flex items-center justify-between gap-3 text-sm">
        <span>{item.name}</span>
        <span className="text-[#7D7B75] tabular-nums">{item.count} observations</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-[#F0EFE9]">
        <span
          className="block h-full bg-[#111111]"
          style={{ width: `${(item.count / max) * 100}%` }}
        />
      </div>
    </li>
  )
}

function RankingPages({
  kind,
  establishmentId,
  periodDays,
  renderItem,
}: {
  kind: 'recurring' | 'new' | 'locations'
  establishmentId: string
  periodDays: DashboardPeriodDays
  renderItem: (item: unknown) => ReactNode
}) {
  const query = useAnalyticsDashboardRankingsInfiniteQuery(
    { establishmentId, periodDays, kind },
  )
  const items = useMemo(
    () => query.data?.pages.flatMap((page) => page.items) ?? [],
    [query.data],
  )
  return (
    <div>
      {query.isLoading ? <p className="text-sm text-[#7D7B75]">Chargement…</p> : null}
      {query.isError ? <p className="text-sm text-[#E24B4A]">Impossible de charger la liste.</p> : null}
      <ul className="flex flex-col gap-3">{items.map((item) => renderItem(item))}</ul>
      {query.hasNextPage ? (
        <button
          type="button"
          className="mt-4 text-sm font-semibold text-[#1F7A4D]"
          onClick={() => void query.fetchNextPage()}
        >
          Charger plus
        </button>
      ) : null}
    </div>
  )
}
