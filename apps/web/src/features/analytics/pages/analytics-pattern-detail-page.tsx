import {
  Activity,
  AlertCircle,
  ArrowLeft,
  Building2,
  CheckCircle2,
  Clock3,
  Flag,
  GitMerge,
  Loader2,
  MoveRight,
  Pencil,
  Repeat2,
  Scissors,
  TrendingUp,
} from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'
import { useMemo, useRef, useState, type ComponentType, type SVGProps } from 'react'

import { useAuth } from '@/app/auth-provider'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import {
  TerrainBottomSheet,
  TerrainCard,
  TerrainEmptyState,
  TerrainErrorState,
  TerrainSectionLabel,
} from '@/components/ui/terrain'
import type {
  AnalyticsMetricComparison,
  AnalyticsOwnerGovernancePatternRef,
  AnalyticsOwnerGovernanceResponse,
  AnalyticsPatternDetailResponse,
  AnalyticsPatternSignalItem,
} from '@/features/analytics/api'
import { AnalyticsApiError, analyticsQueryKeys } from '@/features/analytics/api'
import {
  useAnalyticsPatternGovernanceTargetsInfiniteQuery,
  useAnalyticsPatternDetailQuery,
  useAnalyticsPatternSignalsInfiniteQuery,
  useMergeAnalyticsPatternsMutation,
  useMoveAnalyticsPatternSignalsMutation,
  useRenameAnalyticsPatternMutation,
  useReportAnalyticsPatternIssueMutation,
  useSplitAnalyticsPatternToExistingMutation,
  useSplitAnalyticsPatternToNewMutation,
} from '@/features/analytics/hooks'
import {
  buildAnalyticsPatternDetailPath,
  buildAnalyticsSignalDetailPath,
  buildAnalyticsReturnPath,
  type AnalyticsUrlState,
} from '@/features/analytics/lib/analytics-url-state'
import { switchEstablishment } from '@/features/auth/api'
import type { BootstrapResponse, Membership } from '@/features/auth/types'
import { canShowAnalyticsNavigation } from '@/features/navigation/lib/shared-navigation'
import { resolveApiErrorMessage } from '@/lib/error-message'
import { notifySuccess } from '@/lib/success-toast'
import { terrain } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

type AnalyticsIcon = ComponentType<SVGProps<SVGSVGElement>>

type AnalyticsPatternDetailPageProps = {
  patternId: string
  analyticsState: AnalyticsUrlState
  onNavigate: (pathname: string, options?: { replace?: boolean }) => void
}

const PATTERN_SIGNALS_PAGE_SIZE = 25
const GOVERNANCE_TARGETS_PAGE_SIZE = 20
const PATTERN_ISSUE_COMMENT_MAX_LENGTH = 500
const PATTERN_ISSUE_REASON = 'wrong_pattern' as const
const PATTERN_ISSUE_REPORT_ROLES = new Set(['director', 'manager'])
const OWNER_GOVERNANCE_ROLE = 'owner'

type OwnerGovernanceAction =
  | 'rename'
  | 'merge'
  | 'move'
  | 'split-existing'
  | 'split-new'

function formatNumber(value: number | null): string {
  if (value == null) {
    return '—'
  }

  return new Intl.NumberFormat('fr-FR').format(value)
}

function formatPercentRatio(value: number | null): string {
  if (value == null) {
    return '—'
  }

  return new Intl.NumberFormat('fr-FR', {
    maximumFractionDigits: 1,
    style: 'percent',
  }).format(value)
}

function formatAbsoluteDelta(value: number | null): string {
  if (value == null) {
    return '—'
  }

  const formatted = formatNumber(Math.abs(value))
  if (value > 0) {
    return `+${formatted}`
  }
  if (value < 0) {
    return `-${formatted}`
  }
  return formatted
}

function formatDateTime(value: string | null): string {
  if (!value) {
    return '—'
  }

  return new Intl.DateTimeFormat('fr-FR', {
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    month: 'short',
    year: 'numeric',
  }).format(new Date(value))
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat('fr-FR', {
    day: '2-digit',
    month: 'short',
  }).format(new Date(value))
}

const BACKEND_BUCKET_MONTH_LABELS = [
  'janv.',
  'févr.',
  'mars',
  'avr.',
  'mai',
  'juin',
  'juil.',
  'août',
  'sept.',
  'oct.',
  'nov.',
  'déc.',
]

function formatBackendBucketDate(bucketDate: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(bucketDate)
  if (!match) {
    return bucketDate
  }

  const monthIndex = Number(match[2]) - 1
  const day = Number(match[3])
  const monthLabel = BACKEND_BUCKET_MONTH_LABELS[monthIndex]
  if (!monthLabel || day < 1 || day > 31) {
    return bucketDate
  }

  return `${String(day).padStart(2, '0')} ${monthLabel}`
}

function formatPeriod(start: string, end: string): string {
  return `${formatDate(start)} - ${formatDate(end)}`
}

function activePatternIssueReporterMemberships(
  bootstrap: BootstrapResponse | null | undefined,
): Membership[] {
  return (
    bootstrap?.memberships.filter(
      (membership) =>
        membership.status === 'active' && PATTERN_ISSUE_REPORT_ROLES.has(membership.role),
    ) ?? []
  )
}

function activeOwnerGovernanceMemberships(
  bootstrap: BootstrapResponse | null | undefined,
): Membership[] {
  return (
    bootstrap?.memberships.filter(
      (membership) =>
        membership.status === 'active' && membership.role === OWNER_GOVERNANCE_ROLE,
    ) ?? []
  )
}

function canShowOwnerGovernanceActions(
  bootstrap: BootstrapResponse | null | undefined,
): boolean {
  return activeOwnerGovernanceMemberships(bootstrap).length > 0
}

function resolveSignalOrganizationId(
  bootstrap: BootstrapResponse | null | undefined,
  establishmentId: string,
): string | null {
  return (
    bootstrap?.memberships.find(
      (membership) => membership.establishment_id === establishmentId,
    )?.organization_id ?? null
  )
}

function canShowPatternIssueReportAction({
  bootstrap,
  data,
  analyticsState,
  signal,
}: {
  bootstrap: BootstrapResponse | null | undefined
  data: AnalyticsPatternDetailResponse
  analyticsState: AnalyticsUrlState
  signal: AnalyticsPatternSignalItem
}): boolean {
  const reporterMemberships = activePatternIssueReporterMemberships(bootstrap)
  if (reporterMemberships.length === 0) {
    return false
  }

  const organizationId =
    data.drilldown_context.organization_id ??
    analyticsState.organizationId ??
    resolveSignalOrganizationId(bootstrap, signal.establishment.id)

  if (!organizationId) {
    return true
  }

  return reporterMemberships.some(
    (membership) => membership.organization_id === organizationId,
  )
}

function formatStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    archived: 'Archivé',
    in_progress: 'En cours',
    interesting: 'Intéressant',
    open: 'Ouvert',
    resolved: 'Résolu',
  }

  return labels[status] ?? status.replaceAll('_', ' ')
}

function ComparisonSummary({ comparison }: { comparison: AnalyticsMetricComparison }) {
  const showRelative =
    comparison.relative_change_status === 'computed' && comparison.relative_change != null

  return (
    <div className="flex flex-wrap items-center gap-2 text-xs">
      <Badge variant="outline" className="border-[#E8E6DF] bg-[#F7F6F2] text-[#555]">
        Précédent {formatNumber(comparison.previous_value)}
      </Badge>
      <Badge variant="outline" className="border-[#D8EADA] bg-[#F3FAF5] text-[#24614B]">
        Écart {formatAbsoluteDelta(comparison.absolute_delta)}
      </Badge>
      <span className={terrain.muted}>
        {showRelative ? `${formatPercentRatio(comparison.relative_change)} vs précédent` : 'non comparable'}
      </span>
    </div>
  )
}

function MetricCard({
  title,
  value,
  icon: Icon,
  description,
}: {
  title: string
  value: string
  icon: AnalyticsIcon
  description: string
}) {
  return (
    <TerrainCard className="p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-[#1a1a1a]">{title}</p>
          <p className={cn('mt-1 text-xs leading-5', terrain.muted)}>{description}</p>
        </div>
        <span
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-[#E8F7F0] text-[#114660]"
          aria-hidden
        >
          <Icon className="h-4 w-4" />
        </span>
      </div>
      <p className="mt-4 text-2xl font-semibold text-[#1a1a1a]">{value}</p>
    </TerrainCard>
  )
}

function InlineMetric({
  title,
  value,
  description,
}: {
  title: string
  value: string
  description: string
}) {
  return (
    <div className="rounded-xl border border-[#F0EFE9] bg-[#FBFAF7] p-3">
      <p className="text-xs font-semibold uppercase tracking-[0.04em] text-[#777]">{title}</p>
      <p className="mt-2 text-xl font-semibold text-[#1a1a1a]">{value}</p>
      <p className={cn('mt-1 text-xs leading-5', terrain.muted)}>{description}</p>
    </div>
  )
}

function AnalyticsPatternDetailSkeleton() {
  return (
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4" role="status">
      {Array.from({ length: 4 }).map((_, index) => (
        <TerrainCard key={index} className="p-4">
          <div className="h-4 w-24 rounded-full bg-[#E8E6DF]" />
          <div className="mt-3 h-8 w-20 rounded-full bg-[#E8E6DF]" />
          <div className="mt-3 h-3 w-full rounded-full bg-[#F0EFE9]" />
        </TerrainCard>
      ))}
    </div>
  )
}

function TrendSection({ data }: { data: AnalyticsPatternDetailResponse }) {
  const maxCount = Math.max(1, ...data.trend.map((bucket) => bucket.signal_count))

  return (
    <TerrainCard className="p-4">
      <div className="flex flex-col gap-1">
        <p className="text-sm font-semibold text-[#1a1a1a]">Tendance journalière</p>
        <p className={cn('text-xs leading-5', terrain.muted)}>
          Buckets backend en timezone {data.trend_timezone}.
        </p>
      </div>
      {data.trend.length === 0 ? (
        <TerrainEmptyState title="Aucune tendance disponible" className="mt-4" />
      ) : (
        <div className="mt-4 space-y-2">
          {data.trend.map((bucket) => (
            <div
              key={`${bucket.bucket_start}-${bucket.bucket_end}`}
              className="grid gap-2 text-sm md:grid-cols-[7rem_1fr_4rem]"
            >
              <span className={terrain.muted}>{formatBackendBucketDate(bucket.bucket_date)}</span>
              <div className="h-3 overflow-hidden rounded-full bg-[#F0EFE9]">
                <div
                  className="h-full rounded-full bg-[#114660]"
                  style={{ width: `${(bucket.signal_count / maxCount) * 100}%` }}
                />
              </div>
              <span className="font-semibold text-[#1a1a1a]">
                {formatNumber(bucket.signal_count)}
              </span>
            </div>
          ))}
        </div>
      )}
    </TerrainCard>
  )
}

function StatusDistributionSection({ data }: { data: AnalyticsPatternDetailResponse }) {
  return (
    <TerrainCard className="p-4">
      <p className="text-sm font-semibold text-[#1a1a1a]">Distribution par statut</p>
      {data.status_distribution.length === 0 ? (
        <TerrainEmptyState title="Aucun statut sur cette période" className="mt-4" />
      ) : (
        <div className="mt-4 space-y-2">
          {data.status_distribution.map((bucket) => (
            <div
              key={bucket.status}
              className="flex items-center justify-between rounded-xl border border-[#F0EFE9] bg-[#FBFAF7] px-3 py-2 text-sm"
            >
              <span className={terrain.muted}>{formatStatusLabel(bucket.status)}</span>
              <span className="font-semibold text-[#1a1a1a]">
                {formatNumber(bucket.signal_count)}
              </span>
            </div>
          ))}
        </div>
      )}
    </TerrainCard>
  )
}

function DistributionList({
  title,
  description,
  items,
  bucketCount,
  otherSignalCount,
}: {
  title: string
  description: string
  items: Array<{ id: string | null; name: string; signalCount: number }>
  bucketCount: number
  otherSignalCount: number
}) {
  return (
    <TerrainCard className="p-4">
      <div className="flex flex-col gap-1">
        <p className="text-sm font-semibold text-[#1a1a1a]">{title}</p>
        <p className={cn('text-xs leading-5', terrain.muted)}>{description}</p>
      </div>
      {items.length === 0 ? (
        <TerrainEmptyState title="Aucune donnée sur cette période" className="mt-4" />
      ) : (
        <div className="mt-4 space-y-2">
          {items.map((item) => (
            <div
              key={item.id ?? 'unassigned'}
              className="flex items-center justify-between gap-3 rounded-xl border border-[#F0EFE9] bg-[#FBFAF7] px-3 py-2 text-sm"
            >
              <span className="min-w-0 truncate text-[#1a1a1a]">{item.name}</span>
              <span className="shrink-0 font-semibold text-[#1a1a1a]">
                {formatNumber(item.signalCount)}
              </span>
            </div>
          ))}
        </div>
      )}
      <div className="mt-3 flex flex-wrap gap-2 text-xs">
        <Badge variant="outline" className="border-[#E8E6DF] bg-[#F7F6F2] text-[#555]">
          Buckets {formatNumber(bucketCount)}
        </Badge>
        <Badge variant="outline" className="border-[#E8E6DF] bg-[#F7F6F2] text-[#555]">
          Autres Signals {formatNumber(otherSignalCount)}
        </Badge>
      </div>
    </TerrainCard>
  )
}

function PatternSignalsSection({
  query,
  navigationError,
  openingSignalId,
  onOpenSignal,
  canShowIssueReportAction,
  onReportIssue,
  issueReportSuccess,
}: {
  query: ReturnType<typeof useAnalyticsPatternSignalsInfiniteQuery>
  navigationError: string | null
  openingSignalId: string | null
  onOpenSignal: (item: AnalyticsPatternSignalItem) => void
  canShowIssueReportAction: (item: AnalyticsPatternSignalItem) => boolean
  onReportIssue: (item: AnalyticsPatternSignalItem) => void
  issueReportSuccess: string | null
}) {
  const items = useMemo(
    () => query.data?.pages.flatMap((page) => page.items) ?? [],
    [query.data],
  )

  return (
    <TerrainCard className="p-4">
      <div className="flex flex-col gap-1">
        <p className="text-sm font-semibold text-[#1a1a1a]">Signals du motif</p>
        <p className={cn('text-xs leading-5', terrain.muted)}>
          Liste paginée backend, limitée au payload Analytics safe.
        </p>
      </div>

      {navigationError ? (
        <p className="mt-3 rounded-xl border border-[#F0D9C8] bg-[#FFF7EF] px-3 py-2 text-sm text-[#8A5A00]">
          {navigationError}
        </p>
      ) : null}

      {issueReportSuccess ? (
        <p
          className="mt-3 flex items-center gap-2 rounded-xl border border-[#D8EADA] bg-[#F3FAF5] px-3 py-2 text-sm text-[#24614B]"
          role="status"
        >
          <CheckCircle2 className="h-4 w-4" aria-hidden />
          {issueReportSuccess}
        </p>
      ) : null}

      {query.isLoading ? (
        <div className="mt-4 flex items-center gap-2 text-sm text-[#555]" role="status">
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
          Chargement des Signals...
        </div>
      ) : null}

      {query.isError ? (
        <TerrainErrorState
          className="mt-4"
          message={resolveApiErrorMessage(
            query.error,
            AnalyticsApiError,
            'Impossible de charger les Signals du motif.',
          )}
          onRetry={() => void query.refetch()}
        />
      ) : null}

      {!query.isLoading && !query.isError && items.length === 0 ? (
        <TerrainEmptyState title="Aucun Signal visible" className="mt-4" />
      ) : null}

      {items.length > 0 ? (
        <div
          className="mt-4 divide-y divide-[#F0EFE9] overflow-hidden rounded-xl border border-[#F0EFE9]"
          data-testid="analytics-pattern-signals-list"
        >
          <div className="hidden grid-cols-[minmax(180px,1fr)_120px_150px_150px_minmax(180px,auto)] gap-3 border-b border-[#F0EFE9] bg-[#FBFAF7] px-4 py-3 text-xs font-semibold uppercase tracking-[0.04em] text-[#777] lg:grid">
            <span>Signal</span>
            <span>Statut</span>
            <span>Établissement</span>
            <span>BU</span>
            <span>Action</span>
          </div>
          {items.map((item) => {
            const canReport = canShowIssueReportAction(item)
            return (
              <div
                key={item.signal_id}
                data-testid="analytics-pattern-signal-row"
                className="grid min-w-0 gap-3 px-4 py-3 text-sm transition-colors hover:bg-[#FBFAF7] lg:grid-cols-[minmax(180px,1fr)_120px_150px_150px_minmax(180px,auto)]"
              >
                <button
                  type="button"
                  className="min-w-0 text-left focus:outline-none focus:ring-2 focus:ring-[#114660] focus:ring-offset-2"
                  disabled={openingSignalId === item.signal_id}
                  onClick={() => onOpenSignal(item)}
                >
                  <span className="block break-words font-semibold text-[#1a1a1a]">
                    {item.title}
                  </span>
                  <span className={cn('mt-1 block text-xs leading-5', terrain.muted)}>
                    {item.structured_summary}
                  </span>
                </button>
                <dl className="grid min-w-0 gap-2 sm:grid-cols-3 lg:contents">
                  <div className="min-w-0 rounded-lg bg-[#FBFAF7] px-3 py-2 lg:bg-transparent lg:p-0">
                    <dt className={cn('text-[11px] font-semibold uppercase tracking-[0.04em] lg:hidden', terrain.muted)}>
                      Statut
                    </dt>
                    <dd className="mt-1 text-[#1a1a1a] lg:mt-0">
                      {formatStatusLabel(item.status)}
                    </dd>
                  </div>
                  <div className="min-w-0 rounded-lg bg-[#FBFAF7] px-3 py-2 lg:bg-transparent lg:p-0">
                    <dt className={cn('text-[11px] font-semibold uppercase tracking-[0.04em] lg:hidden', terrain.muted)}>
                      Établissement
                    </dt>
                    <dd className="mt-1 break-words text-[#555] lg:mt-0">
                      {item.establishment.name}
                    </dd>
                  </div>
                  <div className="min-w-0 rounded-lg bg-[#FBFAF7] px-3 py-2 lg:bg-transparent lg:p-0">
                    <dt className={cn('text-[11px] font-semibold uppercase tracking-[0.04em] lg:hidden', terrain.muted)}>
                      BU
                    </dt>
                    <dd className="mt-1 break-words text-[#555] lg:mt-0">
                      {item.responsible_business_unit?.specific_name ?? 'Non assigné'}
                    </dd>
                  </div>
                </dl>
                {canReport ? (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="min-h-11 w-full justify-start text-[#8A5A00] hover:text-[#8A5A00] sm:w-auto lg:min-h-9 lg:justify-self-start"
                    onClick={() => onReportIssue(item)}
                  >
                    <Flag className="mr-2 h-4 w-4" aria-hidden />
                    Signaler un regroupement incorrect
                  </Button>
                ) : null}
                <span className={cn('min-w-0 break-words text-xs lg:col-span-5', terrain.muted)}>
                  Créé {formatDateTime(item.created_at)}
                  {item.resolved_at ? ` · Résolu ${formatDateTime(item.resolved_at)}` : ''}
                  {openingSignalId === item.signal_id ? ' · Ouverture...' : ''}
                </span>
              </div>
            )
          })}
        </div>
      ) : null}

      {query.hasNextPage ? (
        <div className="mt-4">
          <Button
            type="button"
            variant="outline"
            onClick={() => void query.fetchNextPage()}
            disabled={query.isFetchingNextPage}
          >
            {query.isFetchingNextPage ? 'Chargement...' : 'Charger plus'}
          </Button>
        </div>
      ) : null}
    </TerrainCard>
  )
}

function PatternIssueReportSheet({
  signal,
  comment,
  error,
  isPending,
  onCommentChange,
  onClose,
  onSubmit,
}: {
  signal: AnalyticsPatternSignalItem | null
  comment: string
  error: string | null
  isPending: boolean
  onCommentChange: (value: string) => void
  onClose: () => void
  onSubmit: () => void
}) {
  const remainingCharacters = PATTERN_ISSUE_COMMENT_MAX_LENGTH - comment.length

  return (
    <TerrainBottomSheet
      title="Signaler un regroupement incorrect"
      open={Boolean(signal)}
      onClose={onClose}
      dismissible={!isPending}
      footer={
        <div className="flex flex-col gap-2 sm:flex-row sm:justify-end">
          <Button
            type="button"
            variant="outline"
            onClick={onClose}
            disabled={isPending}
          >
            Annuler
          </Button>
          <Button
            type="button"
            onClick={onSubmit}
            disabled={isPending || remainingCharacters < 0}
          >
            {isPending ? 'Envoi...' : 'Envoyer'}
          </Button>
        </div>
      }
    >
      <div className="space-y-4">
        <p className={cn('text-sm leading-6', terrain.muted)}>
          Le signalement crée une demande de revue. Il ne corrige pas automatiquement le motif
          ni les Signals associés.
        </p>
        {signal ? (
          <div className="rounded-xl border border-[#F0EFE9] bg-[#FBFAF7] px-3 py-2 text-sm">
            <p className="font-semibold text-[#1a1a1a]">{signal.title}</p>
            <p className={cn('mt-1 text-xs leading-5', terrain.muted)}>
              {signal.establishment.name}
            </p>
          </div>
        ) : null}
        <label className="block space-y-2">
          <span className="text-sm font-semibold text-[#1a1a1a]">Commentaire optionnel</span>
          <Textarea
            value={comment}
            maxLength={PATTERN_ISSUE_COMMENT_MAX_LENGTH + 1}
            onChange={(event) => onCommentChange(event.target.value)}
            disabled={isPending}
            placeholder="Ajouter un contexte utile pour la revue"
          />
        </label>
        <div className="flex items-center justify-between gap-3 text-xs">
          <span className={terrain.muted}>
            Motif du signalement : regroupement incorrect.
          </span>
          <span className={remainingCharacters < 0 ? 'text-[#B42318]' : terrain.muted}>
            {comment.length}/{PATTERN_ISSUE_COMMENT_MAX_LENGTH}
          </span>
        </div>
        {error ? (
          <p className="rounded-xl border border-[#F0D9C8] bg-[#FFF7EF] px-3 py-2 text-sm text-[#8A5A00]">
            {error}
          </p>
        ) : null}
      </div>
    </TerrainBottomSheet>
  )
}

function loadedPatternSignalItems(
  query: ReturnType<typeof useAnalyticsPatternSignalsInfiniteQuery>,
): AnalyticsPatternSignalItem[] {
  return query.data?.pages.flatMap((page) => page.items) ?? []
}

function OwnerGovernancePanel({
  patternLabel,
  canShow,
  selectedSignalCount,
  success,
  onOpenAction,
}: {
  patternLabel: string
  canShow: boolean
  selectedSignalCount: number
  success: string | null
  onOpenAction: (action: OwnerGovernanceAction) => void
}) {
  if (!canShow) {
    return null
  }

  return (
    <TerrainCard className="border-[#F0D9C8] bg-[#FFFDF9] p-4">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-sm font-semibold text-[#1a1a1a]">Gouvernance Owner</p>
          <p className={cn('mt-1 text-xs leading-5', terrain.muted)}>
            Corrections manuelles du motif “{patternLabel}”. Ces actions ne traitent pas les
            signalements ouverts.
          </p>
          <p className={cn('mt-2 text-xs', terrain.muted)}>
            Signals sélectionnés : {formatNumber(selectedSignalCount)}
          </p>
          {success ? (
            <p
              className="mt-3 flex items-center gap-2 rounded-xl border border-[#D8EADA] bg-[#F3FAF5] px-3 py-2 text-sm text-[#24614B]"
              role="status"
            >
              <CheckCircle2 className="h-4 w-4" aria-hidden />
              {success}
            </p>
          ) : null}
        </div>
        <div className="grid grid-cols-2 gap-2 sm:flex sm:flex-wrap lg:justify-end">
          <Button type="button" variant="outline" size="sm" onClick={() => onOpenAction('rename')}>
            <Pencil className="mr-2 h-4 w-4" aria-hidden />
            Renommer
          </Button>
          <Button type="button" variant="outline" size="sm" onClick={() => onOpenAction('merge')}>
            <GitMerge className="mr-2 h-4 w-4" aria-hidden />
            Fusionner
          </Button>
          <Button type="button" variant="outline" size="sm" onClick={() => onOpenAction('move')}>
            <MoveRight className="mr-2 h-4 w-4" aria-hidden />
            Déplacer
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => onOpenAction('split-existing')}
          >
            <Scissors className="mr-2 h-4 w-4" aria-hidden />
            Split existant
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="col-span-2 sm:col-span-1"
            onClick={() => onOpenAction('split-new')}
          >
            <Scissors className="mr-2 h-4 w-4" aria-hidden />
            Split nouveau
          </Button>
        </div>
      </div>
    </TerrainCard>
  )
}

function GovernanceTargetPicker({
  query,
  selectedTargetId,
  onSelectTarget,
}: {
  query: ReturnType<typeof useAnalyticsPatternGovernanceTargetsInfiniteQuery>
  selectedTargetId: string
  onSelectTarget: (pattern: AnalyticsOwnerGovernancePatternRef) => void
}) {
  const items = useMemo(
    () => query.data?.pages.flatMap((page) => page.items) ?? [],
    [query.data],
  )

  if (query.isLoading) {
    return (
      <p className="flex items-center gap-2 text-sm text-[#555]" role="status">
        <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
        Recherche des motifs...
      </p>
    )
  }

  if (query.isError) {
    return (
      <TerrainErrorState
        message={resolveApiErrorMessage(
          query.error,
          AnalyticsApiError,
          'Impossible de charger les motifs cibles.',
        )}
        onRetry={() => void query.refetch()}
      />
    )
  }

  if (items.length === 0) {
    return <TerrainEmptyState title="Aucun motif cible disponible" />
  }

  return (
    <div className="space-y-3">
      <div className="max-h-64 space-y-2 overflow-y-auto rounded-xl border border-[#F0EFE9] p-2">
        {items.map((item) => {
          const selected = selectedTargetId === item.pattern_id
          return (
            <button
              key={item.pattern_id}
              type="button"
              className={cn(
                'w-full rounded-xl border px-3 py-2 text-left text-sm transition-colors focus:outline-none focus:ring-2 focus:ring-[#114660] focus:ring-offset-2',
                selected
                  ? 'border-[#114660] bg-[#E8F7F0]'
                  : 'border-[#F0EFE9] bg-white hover:bg-[#FBFAF7]',
              )}
              aria-pressed={selected}
              onClick={() => onSelectTarget(item)}
            >
              <span className="block font-semibold text-[#1a1a1a]">{item.label}</span>
              <span className={cn('text-xs', terrain.muted)}>{item.normalized_label}</span>
            </button>
          )
        })}
      </div>
      {query.hasNextPage ? (
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => void query.fetchNextPage()}
          disabled={query.isFetchingNextPage}
        >
          {query.isFetchingNextPage ? 'Chargement...' : 'Charger plus de motifs'}
        </Button>
      ) : null}
    </div>
  )
}

function GovernanceSignalSelector({
  signals,
  selectedSignalIds,
  onToggleSignal,
}: {
  signals: AnalyticsPatternSignalItem[]
  selectedSignalIds: string[]
  onToggleSignal: (signalId: string) => void
}) {
  if (signals.length === 0) {
    return <TerrainEmptyState title="Aucun Signal chargé à sélectionner" />
  }

  return (
    <div className="max-h-64 space-y-2 overflow-y-auto rounded-xl border border-[#F0EFE9] p-2">
      {signals.map((signal) => (
        <label
          key={signal.signal_id}
          className="flex cursor-pointer items-start gap-3 rounded-xl border border-[#F0EFE9] bg-white px-3 py-2 text-sm"
        >
          <input
            type="checkbox"
            className="mt-1 h-4 w-4 rounded border-[#D8D3C7]"
            checked={selectedSignalIds.includes(signal.signal_id)}
            onChange={() => onToggleSignal(signal.signal_id)}
          />
          <span className="min-w-0">
            <span className="block font-semibold text-[#1a1a1a]">{signal.title}</span>
            <span className={cn('block text-xs leading-5', terrain.muted)}>
              {signal.establishment.name} · {formatStatusLabel(signal.status)}
            </span>
          </span>
        </label>
      ))}
    </div>
  )
}

function OwnerGovernanceSheet({
  action,
  patternLabel,
  renameLabel,
  splitLabel,
  targetSearch,
  selectedTargetId,
  selectedSignalIds,
  loadedSignals,
  targetQuery,
  error,
  success,
  isPending,
  onRenameLabelChange,
  onSplitLabelChange,
  onTargetSearchChange,
  onSelectTarget,
  onToggleSignal,
  onClose,
  onSubmit,
}: {
  action: OwnerGovernanceAction | null
  patternLabel: string
  renameLabel: string
  splitLabel: string
  targetSearch: string
  selectedTargetId: string
  selectedSignalIds: string[]
  loadedSignals: AnalyticsPatternSignalItem[]
  targetQuery: ReturnType<typeof useAnalyticsPatternGovernanceTargetsInfiniteQuery>
  error: string | null
  success: string | null
  isPending: boolean
  onRenameLabelChange: (value: string) => void
  onSplitLabelChange: (value: string) => void
  onTargetSearchChange: (value: string) => void
  onSelectTarget: (pattern: AnalyticsOwnerGovernancePatternRef) => void
  onToggleSignal: (signalId: string) => void
  onClose: () => void
  onSubmit: () => void
}) {
  const requiresTarget = action === 'merge' || action === 'move' || action === 'split-existing'
  const requiresSignals =
    action === 'move' || action === 'split-existing' || action === 'split-new'
  const canSubmit =
    Boolean(action) &&
    !isPending &&
    (action !== 'rename' || renameLabel.trim().length > 0) &&
    (action !== 'split-new' || splitLabel.trim().length > 0) &&
    (!requiresTarget || Boolean(selectedTargetId)) &&
    (!requiresSignals || selectedSignalIds.length > 0)

  const titleByAction: Record<OwnerGovernanceAction, string> = {
    rename: 'Renommer le motif',
    merge: 'Fusionner le motif',
    move: 'Déplacer des Signals',
    'split-existing': 'Séparer vers un motif existant',
    'split-new': 'Séparer vers un nouveau motif',
  }

  return (
    <TerrainBottomSheet
      title={action ? titleByAction[action] : 'Gouvernance Owner'}
      open={Boolean(action)}
      onClose={onClose}
      dismissible={!isPending}
      footer={
        <div className="flex flex-col gap-2 sm:flex-row sm:justify-end">
          <Button type="button" variant="outline" onClick={onClose} disabled={isPending}>
            Annuler
          </Button>
          <Button type="button" onClick={onSubmit} disabled={!canSubmit}>
            {isPending ? 'Application...' : 'Confirmer'}
          </Button>
        </div>
      }
    >
      <div className="space-y-4">
        <p className={cn('text-sm leading-6', terrain.muted)}>
          Action Owner sur “{patternLabel}”. Le backend vérifie les permissions,
          assignments courants et conflits éventuels.
        </p>

        {action === 'rename' ? (
          <label className="block space-y-2">
            <span className="text-sm font-semibold text-[#1a1a1a]">Nouveau libellé</span>
            <Input
              value={renameLabel}
              onChange={(event) => onRenameLabelChange(event.target.value)}
              disabled={isPending}
            />
          </label>
        ) : null}

        {action === 'split-new' ? (
          <label className="block space-y-2">
            <span className="text-sm font-semibold text-[#1a1a1a]">Libellé du nouveau motif</span>
            <Input
              value={splitLabel}
              onChange={(event) => onSplitLabelChange(event.target.value)}
              disabled={isPending}
            />
          </label>
        ) : null}

        {requiresTarget ? (
          <div className="space-y-3">
            <label className="block space-y-2">
              <span className="text-sm font-semibold text-[#1a1a1a]">Motif cible</span>
              <Input
                value={targetSearch}
                onChange={(event) => onTargetSearchChange(event.target.value)}
                disabled={isPending}
                placeholder="Rechercher un motif cible"
              />
            </label>
            <GovernanceTargetPicker
              query={targetQuery}
              selectedTargetId={selectedTargetId}
              onSelectTarget={onSelectTarget}
            />
          </div>
        ) : null}

        {requiresSignals ? (
          <div className="space-y-2">
            <p className="text-sm font-semibold text-[#1a1a1a]">Signals chargés</p>
            <GovernanceSignalSelector
              signals={loadedSignals}
              selectedSignalIds={selectedSignalIds}
              onToggleSignal={onToggleSignal}
            />
          </div>
        ) : null}

        {success ? (
          <p
            className="flex items-center gap-2 rounded-xl border border-[#D8EADA] bg-[#F3FAF5] px-3 py-2 text-sm text-[#24614B]"
            role="status"
          >
            <CheckCircle2 className="h-4 w-4" aria-hidden />
            {success}
          </p>
        ) : null}

        {error ? (
          <p className="rounded-xl border border-[#F0D9C8] bg-[#FFF7EF] px-3 py-2 text-sm text-[#8A5A00]">
            {error}
          </p>
        ) : null}
      </div>
    </TerrainBottomSheet>
  )
}

function AnalyticsPatternDetailContent({
  data,
  onBack,
  patternSignalsQuery,
  signalNavigationError,
  openingSignalId,
  onOpenSignal,
  canShowIssueReportAction,
  onReportIssue,
  issueReportSuccess,
  canShowOwnerGovernance,
  selectedGovernanceSignalIds,
  governanceSuccess,
  onOpenGovernanceAction,
}: {
  data: AnalyticsPatternDetailResponse
  onBack: () => void
  patternSignalsQuery: ReturnType<typeof useAnalyticsPatternSignalsInfiniteQuery>
  signalNavigationError: string | null
  openingSignalId: string | null
  onOpenSignal: (item: AnalyticsPatternSignalItem) => void
  canShowIssueReportAction: (item: AnalyticsPatternSignalItem) => boolean
  onReportIssue: (item: AnalyticsPatternSignalItem) => void
  issueReportSuccess: string | null
  canShowOwnerGovernance: boolean
  selectedGovernanceSignalIds: string[]
  governanceSuccess: string | null
  onOpenGovernanceAction: (action: OwnerGovernanceAction) => void
}) {
  return (
    <>
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <TerrainSectionLabel>Motif Analytics</TerrainSectionLabel>
          <h1 className="text-2xl font-semibold text-[#1a1a1a] md:text-3xl">
            {data.identity.label}
          </h1>
          <p className={cn('mt-1 text-sm', terrain.muted)}>
            {formatPeriod(data.current_period.period_start, data.current_period.period_end)}
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <Badge variant="outline" className="border-[#D8EADA] bg-[#F3FAF5] text-[#24614B]">
              {data.is_recurrent ? 'Récurrent' : 'Non récurrent'}
            </Badge>
            <Badge variant="outline" className="border-[#E8E6DF] bg-[#F7F6F2] text-[#555]">
              Statut {data.identity.status}
            </Badge>
          </div>
        </div>
        <Button type="button" variant="outline" onClick={onBack}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Retour aux motifs
        </Button>
      </div>

      <OwnerGovernancePanel
        patternLabel={data.identity.label}
        canShow={canShowOwnerGovernance}
        selectedSignalCount={selectedGovernanceSignalIds.length}
        success={governanceSuccess}
        onOpenAction={onOpenGovernanceAction}
      />

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          title="Signals"
          value={formatNumber(data.metrics.signal_count)}
          description="Occurrences visibles dans la période."
          icon={Activity}
        />
        <MetricCard
          title="À traiter"
          value={formatNumber(data.metrics.actionable_signal_count)}
          description="Population actionable backend."
          icon={AlertCircle}
        />
        <MetricCard
          title="Dernière apparition"
          value={formatDateTime(data.metrics.last_seen_at)}
          description="Dernier Signal contributeur visible."
          icon={Clock3}
        />
        <MetricCard
          title="Établissements"
          value={formatNumber(data.metrics.establishment_count)}
          description="Établissements visibles contributeurs."
          icon={Building2}
        />
      </div>

      <TerrainCard className="p-4">
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-[#114660]" aria-hidden />
            <p className="text-sm font-semibold text-[#1a1a1a]">Comparaison</p>
          </div>
          <p className={cn('text-xs leading-5', terrain.muted)}>
            Période précédente :{' '}
            {formatPeriod(data.previous_period.period_start, data.previous_period.period_end)}.
          </p>
          <ComparisonSummary comparison={data.metrics.signal_count_comparison} />
        </div>
      </TerrainCard>

      <TerrainCard className="p-4">
        <div className="flex items-center gap-2">
          <Repeat2 className="h-4 w-4 text-[#114660]" aria-hidden />
          <p className="text-sm font-semibold text-[#1a1a1a]">Récurrence</p>
        </div>
        <div className="mt-4 grid gap-3 md:grid-cols-3">
          <InlineMetric
            title="Occurrences 30j"
            value={formatNumber(data.occurrence_count_30d)}
            description="Fenêtre fixe backend."
          />
          <InlineMetric
            title="Jours distincts"
            value={formatNumber(data.distinct_day_count_30d)}
            description="Jours locaux par établissement."
          />
          <InlineMetric
            title="Fenêtre"
            value={formatPeriod(
              data.recurrence_window.window_start,
              data.recurrence_window.window_end,
            )}
            description={`Statut ${data.recurrence_status}.`}
          />
        </div>
      </TerrainCard>

      <TrendSection data={data} />

      <div className="grid gap-3 lg:grid-cols-2">
        <StatusDistributionSection data={data} />
        <DistributionList
          title="Établissements concernés"
          description="Résumé borné retourné par le backend."
          items={data.establishments.map((item) => ({
            id: item.establishment_id,
            name: item.name,
            signalCount: item.signal_count,
          }))}
          bucketCount={data.establishment_bucket_count}
          otherSignalCount={data.establishment_other_signal_count}
        />
      </div>

      <DistributionList
        title="BU responsables"
        description="Résumé borné des Business Units responsables."
        items={data.responsible_business_units.map((item) => ({
          id: item.business_unit_id,
          name: item.name,
          signalCount: item.signal_count,
        }))}
        bucketCount={data.business_unit_bucket_count}
        otherSignalCount={data.business_unit_other_signal_count}
      />

      <PatternSignalsSection
        query={patternSignalsQuery}
        navigationError={signalNavigationError}
        openingSignalId={openingSignalId}
        onOpenSignal={onOpenSignal}
        canShowIssueReportAction={canShowIssueReportAction}
        onReportIssue={onReportIssue}
        issueReportSuccess={issueReportSuccess}
      />
    </>
  )
}

export function AnalyticsPatternDetailPage({
  patternId,
  analyticsState,
  onNavigate,
}: AnalyticsPatternDetailPageProps) {
  const queryClient = useQueryClient()
  const { bootstrap, isBootstrapping, isReady } = useAuth()
  const canAccessAnalytics = canShowAnalyticsNavigation(bootstrap)
  const canShowOwnerGovernance = canShowOwnerGovernanceActions(bootstrap)
  const [signalNavigationError, setSignalNavigationError] = useState<string | null>(null)
  const [openingSignalId, setOpeningSignalId] = useState<string | null>(null)
  const [reportSignal, setReportSignal] = useState<AnalyticsPatternSignalItem | null>(null)
  const [reportComment, setReportComment] = useState('')
  const [reportError, setReportError] = useState<string | null>(null)
  const [reportSuccess, setReportSuccess] = useState<string | null>(null)
  const [governanceAction, setGovernanceAction] = useState<OwnerGovernanceAction | null>(null)
  const [governanceRenameLabel, setGovernanceRenameLabel] = useState('')
  const [governanceSplitLabel, setGovernanceSplitLabel] = useState('')
  const [governanceTargetSearch, setGovernanceTargetSearch] = useState('')
  const [governanceSelectedTarget, setGovernanceSelectedTarget] =
    useState<AnalyticsOwnerGovernancePatternRef | null>(null)
  const [governanceSelectedSignalIds, setGovernanceSelectedSignalIds] = useState<string[]>([])
  const [governanceError, setGovernanceError] = useState<string | null>(null)
  const [governanceSuccess, setGovernanceSuccess] = useState<string | null>(null)
  const issueReportSubmitLockedRef = useRef(false)
  const governanceSubmitLockedRef = useRef(false)
  const activeEstablishmentId = bootstrap?.active_membership?.establishment_id ?? null
  const detailQuery = useAnalyticsPatternDetailQuery(patternId, analyticsState, {
    enabled: isReady && !isBootstrapping && canAccessAnalytics,
  })
  const patternSignalsQuery = useAnalyticsPatternSignalsInfiniteQuery(patternId, analyticsState, {
    enabled: isReady && !isBootstrapping && canAccessAnalytics && Boolean(detailQuery.data),
    pageSize: PATTERN_SIGNALS_PAGE_SIZE,
  })
  const governanceTargetsQuery = useAnalyticsPatternGovernanceTargetsInfiniteQuery(patternId, {
    enabled:
      isReady &&
      !isBootstrapping &&
      canAccessAnalytics &&
      canShowOwnerGovernance &&
      Boolean(governanceAction) &&
      governanceAction !== 'rename' &&
      governanceAction !== 'split-new',
    q: governanceTargetSearch,
    pageSize: GOVERNANCE_TARGETS_PAGE_SIZE,
  })
  const issueReportMutation = useReportAnalyticsPatternIssueMutation()
  const renameMutation = useRenameAnalyticsPatternMutation()
  const mergeMutation = useMergeAnalyticsPatternsMutation()
  const moveMutation = useMoveAnalyticsPatternSignalsMutation()
  const splitExistingMutation = useSplitAnalyticsPatternToExistingMutation()
  const splitNewMutation = useSplitAnalyticsPatternToNewMutation()
  const backPath = buildAnalyticsReturnPath(analyticsState)
  const loadedSignals = loadedPatternSignalItems(patternSignalsQuery)
  const governanceIsPending =
    renameMutation.isPending ||
    mergeMutation.isPending ||
    moveMutation.isPending ||
    splitExistingMutation.isPending ||
    splitNewMutation.isPending

  function navigateBack() {
    onNavigate(backPath)
  }

  async function openSignal(item: AnalyticsPatternSignalItem) {
    const path = buildAnalyticsSignalDetailPath(item.signal_id, {
      patternId,
      state: analyticsState,
    })
    setSignalNavigationError(null)
    setOpeningSignalId(item.signal_id)
    try {
      if (activeEstablishmentId !== item.establishment.id) {
        await switchEstablishment({ establishment_id: item.establishment.id })
      }
      onNavigate(path)
    } catch (error) {
      setSignalNavigationError(
        error instanceof Error ? error.message : 'Impossible d’ouvrir ce Signal.',
      )
    } finally {
      setOpeningSignalId(null)
    }
  }

  function openIssueReport(item: AnalyticsPatternSignalItem) {
    setReportSignal(item)
    setReportComment('')
    setReportError(null)
    setReportSuccess(null)
  }

  function openGovernanceAction(action: OwnerGovernanceAction) {
    const label = detailQuery.data?.identity.label ?? ''
    setGovernanceAction(action)
    setGovernanceRenameLabel(label)
    setGovernanceSplitLabel('')
    setGovernanceTargetSearch('')
    setGovernanceSelectedTarget(null)
    setGovernanceSelectedSignalIds([])
    setGovernanceError(null)
    setGovernanceSuccess(null)
  }

  function closeGovernanceSheet() {
    if (governanceIsPending) {
      return
    }
    setGovernanceAction(null)
    setGovernanceError(null)
    setGovernanceSuccess(null)
    setGovernanceSelectedTarget(null)
    setGovernanceSelectedSignalIds([])
    setGovernanceTargetSearch('')
  }

  function toggleGovernanceSignal(signalId: string) {
    setGovernanceSelectedSignalIds((current) =>
      current.includes(signalId)
        ? current.filter((candidate) => candidate !== signalId)
        : [...current, signalId],
    )
  }

  function ownerGovernanceErrorMessage(error: unknown) {
    return resolveApiErrorMessage(
      error,
      AnalyticsApiError,
      'Impossible d’appliquer cette correction Owner.',
    )
  }

  async function invalidateRenameGovernanceQueries() {
    await Promise.all([
      queryClient.invalidateQueries({
        queryKey: analyticsQueryKeys.patternDetail(patternId, analyticsState),
      }),
      queryClient.invalidateQueries({ queryKey: ['analytics', 'patterns'] }),
    ])
  }

  async function invalidateStructuralGovernanceQueries(
    result: AnalyticsOwnerGovernanceResponse,
    options: { includeSourceActive?: boolean } = {},
  ) {
    const targetPatternId = result.target_pattern?.pattern_id
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['analytics', 'dashboard'] }),
      queryClient.invalidateQueries({ queryKey: ['analytics', 'patterns'] }),
      queryClient.invalidateQueries({
        queryKey: analyticsQueryKeys.patternDetail(patternId, analyticsState),
        type: options.includeSourceActive === false ? 'inactive' : 'all',
      }),
      queryClient.invalidateQueries({
        queryKey: analyticsQueryKeys.patternSignals(
          patternId,
          analyticsState,
          PATTERN_SIGNALS_PAGE_SIZE,
        ),
        type: options.includeSourceActive === false ? 'inactive' : 'all',
      }),
      targetPatternId
        ? queryClient.invalidateQueries({
            queryKey: analyticsQueryKeys.patternDetail(targetPatternId, analyticsState),
          })
        : Promise.resolve(),
      targetPatternId
        ? queryClient.invalidateQueries({
            queryKey: analyticsQueryKeys.patternSignals(
              targetPatternId,
              analyticsState,
              PATTERN_SIGNALS_PAGE_SIZE,
            ),
          })
        : Promise.resolve(),
    ])
  }

  async function submitGovernanceAction() {
    if (!governanceAction || governanceIsPending || governanceSubmitLockedRef.current) {
      return
    }
    governanceSubmitLockedRef.current = true
    setGovernanceError(null)
    setGovernanceSuccess(null)
    try {
      if (governanceAction === 'rename') {
        const result = await renameMutation.mutateAsync({
          patternId,
          body: { label: governanceRenameLabel },
        })
        await invalidateRenameGovernanceQueries()
        setGovernanceSuccess(`Motif renommé en “${result.source_pattern.label}”.`)
        setGovernanceAction(null)
        return
      }

      if (governanceAction === 'merge') {
        if (!governanceSelectedTarget) {
          return
        }
        const result = await mergeMutation.mutateAsync({
          patternId,
          body: { target_pattern_id: governanceSelectedTarget.pattern_id },
        })
        const targetPatternId = result.target_pattern?.pattern_id
        notifySuccess({
          message: `Fusion appliquée : ${formatNumber(result.moved_signal_count)} Signal(s) déplacé(s).`,
          kind: 'updated',
        })
        if (targetPatternId) {
          onNavigate(buildAnalyticsPatternDetailPath(targetPatternId, analyticsState), {
            replace: true,
          })
        }
        await invalidateStructuralGovernanceQueries(result, { includeSourceActive: false })
        setGovernanceAction(null)
        return
      }

      if (governanceAction === 'move') {
        if (!governanceSelectedTarget || governanceSelectedSignalIds.length === 0) {
          return
        }
        const result = await moveMutation.mutateAsync({
          patternId,
          body: {
            target_pattern_id: governanceSelectedTarget.pattern_id,
            signal_ids: governanceSelectedSignalIds,
          },
        })
        await invalidateStructuralGovernanceQueries(result)
        setGovernanceSelectedSignalIds([])
        setGovernanceSuccess(`${formatNumber(result.moved_signal_count)} Signal(s) déplacé(s).`)
        setGovernanceAction(null)
        return
      }

      if (governanceAction === 'split-existing') {
        if (!governanceSelectedTarget || governanceSelectedSignalIds.length === 0) {
          return
        }
        const result = await splitExistingMutation.mutateAsync({
          patternId,
          body: {
            target_pattern_id: governanceSelectedTarget.pattern_id,
            signal_ids: governanceSelectedSignalIds,
          },
        })
        await invalidateStructuralGovernanceQueries(result)
        setGovernanceSelectedSignalIds([])
        setGovernanceSuccess(`${formatNumber(result.moved_signal_count)} Signal(s) séparé(s).`)
        setGovernanceAction(null)
        return
      }

      if (governanceAction === 'split-new') {
        if (governanceSelectedSignalIds.length === 0) {
          return
        }
        const result = await splitNewMutation.mutateAsync({
          patternId,
          body: {
            label: governanceSplitLabel,
            signal_ids: governanceSelectedSignalIds,
          },
        })
        const targetPatternId = result.target_pattern?.pattern_id
        await invalidateStructuralGovernanceQueries(result)
        setGovernanceAction(null)
        if (targetPatternId) {
          onNavigate(buildAnalyticsPatternDetailPath(targetPatternId, analyticsState))
        }
      }
    } catch (error) {
      setGovernanceError(ownerGovernanceErrorMessage(error))
    } finally {
      governanceSubmitLockedRef.current = false
    }
  }

  function closeIssueReport() {
    if (issueReportMutation.isPending) {
      return
    }
    setReportSignal(null)
    setReportComment('')
    setReportError(null)
  }

  async function submitIssueReport() {
    if (
      !reportSignal ||
      issueReportMutation.isPending ||
      issueReportSubmitLockedRef.current
    ) {
      return
    }
    issueReportSubmitLockedRef.current = true
    setReportError(null)
    try {
      await issueReportMutation.mutateAsync({
        patternId,
        signalId: reportSignal.signal_id,
        body: {
          reason: PATTERN_ISSUE_REASON,
          comment: reportComment,
        },
      })
      setReportSuccess('Signalement envoyé pour revue.')
      setReportSignal(null)
      setReportComment('')
    } catch (error) {
      setReportError(
        resolveApiErrorMessage(
          error,
          AnalyticsApiError,
          'Impossible d’envoyer ce signalement.',
        ),
      )
    } finally {
      issueReportSubmitLockedRef.current = false
    }
  }

  if (!isReady || isBootstrapping) {
    return <p className={cn('px-3 py-4 text-sm', terrain.muted)}>Chargement...</p>
  }

  if (!canAccessAnalytics) {
    return (
      <div className="flex min-h-0 flex-1 flex-col px-3 pb-4 pt-3">
        <TerrainErrorState message="Analytics est disponible pour les propriétaires, directeurs et managers." />
      </div>
    )
  }

  const isNotFound =
    detailQuery.error instanceof AnalyticsApiError &&
    detailQuery.error.code === 'analytics_pattern_not_found'

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4 px-3 pb-5 pt-3 md:px-5 lg:px-6">
      {detailQuery.isLoading ? <AnalyticsPatternDetailSkeleton /> : null}

      {detailQuery.isError ? (
        isNotFound ? (
          <TerrainEmptyState
            title="Motif introuvable"
            description="Ce motif est introuvable ou non accessible dans le contexte Analytics courant."
          />
        ) : (
          <TerrainErrorState
            message={resolveApiErrorMessage(
              detailQuery.error,
              AnalyticsApiError,
              'Impossible de charger ce motif.',
            )}
            onRetry={() => void detailQuery.refetch()}
          />
        )
      ) : null}

      {detailQuery.data ? (
        <>
          <AnalyticsPatternDetailContent
            data={detailQuery.data}
            onBack={navigateBack}
            patternSignalsQuery={patternSignalsQuery}
            signalNavigationError={signalNavigationError}
            openingSignalId={openingSignalId}
            onOpenSignal={(item) => void openSignal(item)}
            canShowIssueReportAction={(item) =>
              canShowPatternIssueReportAction({
                bootstrap,
                data: detailQuery.data,
                analyticsState,
                signal: item,
              })
            }
            onReportIssue={openIssueReport}
            issueReportSuccess={reportSuccess}
            canShowOwnerGovernance={canShowOwnerGovernance}
            selectedGovernanceSignalIds={governanceSelectedSignalIds}
            governanceSuccess={governanceSuccess}
            onOpenGovernanceAction={openGovernanceAction}
          />
          <OwnerGovernanceSheet
            action={governanceAction}
            patternLabel={detailQuery.data.identity.label}
            renameLabel={governanceRenameLabel}
            splitLabel={governanceSplitLabel}
            targetSearch={governanceTargetSearch}
            selectedTargetId={governanceSelectedTarget?.pattern_id ?? ''}
            selectedSignalIds={governanceSelectedSignalIds}
            loadedSignals={loadedSignals}
            targetQuery={governanceTargetsQuery}
            error={governanceError}
            success={governanceSuccess}
            isPending={governanceIsPending}
            onRenameLabelChange={setGovernanceRenameLabel}
            onSplitLabelChange={setGovernanceSplitLabel}
            onTargetSearchChange={(value) => {
              setGovernanceTargetSearch(value)
              setGovernanceSelectedTarget(null)
            }}
            onSelectTarget={setGovernanceSelectedTarget}
            onToggleSignal={toggleGovernanceSignal}
            onClose={closeGovernanceSheet}
            onSubmit={() => void submitGovernanceAction()}
          />
          <PatternIssueReportSheet
            signal={reportSignal}
            comment={reportComment}
            error={reportError}
            isPending={issueReportMutation.isPending}
            onCommentChange={setReportComment}
            onClose={closeIssueReport}
            onSubmit={() => void submitIssueReport()}
          />
        </>
      ) : null}
    </div>
  )
}
