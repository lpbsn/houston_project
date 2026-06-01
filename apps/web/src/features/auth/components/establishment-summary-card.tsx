import { Building2, Crown, LoaderCircle, UserRound, UsersRound } from 'lucide-react'
import type { ReactNode } from 'react'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import type { WorkspaceSummaryResponse } from '@/features/auth/types'

type EstablishmentSummaryCardProps = {
  errorMessage: string | null
  isLoading: boolean
  summary: WorkspaceSummaryResponse | null
}

export function EstablishmentSummaryCard({
  errorMessage,
  isLoading,
  summary,
}: EstablishmentSummaryCardProps) {
  if (isLoading) {
    return (
      <Card className="rounded-[1.85rem] border-[#ece5da] bg-[#fffdf9] shadow-[0_24px_52px_-40px_rgba(46,72,173,0.28)]">
        <CardContent className="flex items-center gap-3 px-6 py-8 text-sm text-muted-foreground">
          <LoaderCircle className="size-4 animate-spin text-[color:var(--primary)]" />
          Loading establishment summary...
        </CardContent>
      </Card>
    )
  }

  if (errorMessage) {
    return (
      <Card className="rounded-[1.85rem] border-[#ece5da] bg-[#fffdf9] shadow-[0_24px_52px_-40px_rgba(46,72,173,0.28)]">
        <CardContent className="px-6 py-8 text-sm text-[#9d3b33]">{errorMessage}</CardContent>
      </Card>
    )
  }

  if (!summary) {
    return (
      <Card className="rounded-[1.85rem] border-[#ece5da] bg-[#fffdf9] shadow-[0_24px_52px_-40px_rgba(46,72,173,0.28)]">
        <CardContent className="px-6 py-8 text-sm text-muted-foreground">
          Select an establishment to view its summary.
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="rounded-[1.85rem] border-[#ece5da] bg-[#fffdf9] shadow-[0_24px_52px_-40px_rgba(46,72,173,0.28)]">
      <CardHeader className="gap-3">
        <div className="space-y-2">
          <CardTitle className="text-[1.7rem] font-black tracking-[-0.06em]">
            {summary.establishment.name}
          </CardTitle>
          <CardDescription className="text-sm leading-6">
            Overview of leadership and active team members for this establishment.
          </CardDescription>
        </div>
      </CardHeader>

      <CardContent className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <SummaryTile
          icon={<Building2 className="size-4" />}
          label="Establishment"
          value={summary.establishment.name}
        />
        <SummaryTile
          icon={<Crown className="size-4" />}
          label="Owner"
          value={summary.owner?.display_name ?? 'Not assigned'}
        />
        <SummaryTile
          icon={<UserRound className="size-4" />}
          label="Director"
          value={
            summary.director
              ? `${summary.director.display_name}${summary.director.status === 'invited' ? ' (invited)' : ''}`
              : 'Not assigned'
          }
        />
        <SummaryTile
          icon={<UsersRound className="size-4" />}
          label="Active members"
          value={String(summary.active_membership_count)}
        />
      </CardContent>
    </Card>
  )
}

function SummaryTile({
  icon,
  label,
  value,
}: {
  icon: ReactNode
  label: string
  value: string
}) {
  return (
    <div className="rounded-[1.35rem] border border-[#ece5da] bg-white px-4 py-4 shadow-[0_14px_34px_-32px_rgba(46,72,173,0.22)]">
      <div className="mb-3 flex items-center gap-2 text-sm font-medium text-muted-foreground">
        <span className="rounded-full bg-[color:var(--primary)]/10 p-2 text-[color:var(--primary)]">
          {icon}
        </span>
        {label}
      </div>
      <div className="text-base font-bold tracking-[-0.03em] text-foreground">{value}</div>
    </div>
  )
}
