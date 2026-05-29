import { Building2, CheckCircle2, CircleAlert, Gauge, Layers3 } from 'lucide-react'
import type { ReactNode } from 'react'

import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import type {
  ActivationSummaryResponse,
  OnboardingSessionResponse,
  RuntimeConfigResponse,
} from '@/features/onboarding/types'

type OnboardingHeroCardProps = {
  activationSummary: ActivationSummaryResponse | null
  runtimeConfig: RuntimeConfigResponse | null
  session: OnboardingSessionResponse
}

export function OnboardingHeroCard({
  activationSummary,
  runtimeConfig,
  session,
}: OnboardingHeroCardProps) {
  const blockerCount = activationSummary?.blockers.length ?? 0
  const readinessLabel = activationSummary?.readiness.is_ready ? 'Ready' : 'In progress'
  const readinessIcon = activationSummary?.readiness.is_ready ? (
    <CheckCircle2 className="size-4" />
  ) : (
    <Gauge className="size-4" />
  )

  return (
    <Card className="rounded-[1.85rem] border-[#ece5da] bg-[#fffdf9] shadow-[0_24px_52px_-40px_rgba(46,72,173,0.28)]">
      <CardHeader className="gap-3">
        <div className="flex flex-wrap gap-2">
          <Badge className="bg-[color:var(--primary)] text-primary-foreground">
            {session.status}
          </Badge>
          <Badge variant="outline" className="border-[#ebe2d5] bg-[#fbf7f0]">
            {session.source_mode}
          </Badge>
          <Badge variant="outline" className="border-[#ebe2d5] bg-white">
            {session.establishment.status}
          </Badge>
        </div>

        <div className="space-y-2">
          <CardTitle className="text-[1.7rem] font-black tracking-[-0.06em]">
            {session.establishment.name}
          </CardTitle>
          <CardDescription className="text-sm leading-6">
            {session.organization.name} · Current step: {session.current_step}
          </CardDescription>
        </div>
      </CardHeader>

      <CardContent className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <SummaryTile
          icon={<Building2 className="size-4" />}
          label="Readiness"
          value={readinessLabel}
          supporting={
            activationSummary
              ? activationSummary.effective_can_activate
                ? 'Backend allows mark-ready'
                : 'Backend has not allowed mark-ready'
              : 'Loading backend summary'
          }
          accent={activationSummary?.readiness.is_ready ? 'success' : 'default'}
          valueIcon={readinessIcon}
        />
        <SummaryTile
          icon={<Layers3 className="size-4" />}
          label="Modules"
          value={`${activationSummary?.active_modules.length ?? runtimeConfig?.active_modules.length ?? 0}`}
          supporting="Active runtime modules"
        />
        <SummaryTile
          icon={<Gauge className="size-4" />}
          label="Domains"
          value={`${activationSummary?.active_domains.length ?? runtimeConfig?.active_domains.length ?? 0}`}
          supporting="Active operational domains"
        />
        <SummaryTile
          icon={<CircleAlert className="size-4" />}
          label="Blockers"
          value={`${blockerCount}`}
          supporting={blockerCount === 1 ? 'Backend blocker' : 'Backend blockers'}
          accent={blockerCount > 0 ? 'danger' : 'success'}
        />
      </CardContent>
    </Card>
  )
}

function SummaryTile({
  accent = 'default',
  icon,
  label,
  supporting,
  value,
  valueIcon,
}: {
  accent?: 'default' | 'danger' | 'success'
  icon: ReactNode
  label: string
  supporting: string
  value: string
  valueIcon?: ReactNode
}) {
  const iconClassName =
    accent === 'danger'
      ? 'bg-[#fff3f2] text-[#9d3b33]'
      : accent === 'success'
        ? 'bg-emerald-50 text-emerald-700'
        : 'bg-[color:var(--primary)]/10 text-[color:var(--primary)]'

  return (
    <div className="rounded-[1.35rem] border border-[#ece5da] bg-white px-4 py-4 shadow-[0_14px_34px_-32px_rgba(46,72,173,0.22)]">
      <div className="mb-3 flex items-center gap-2 text-sm font-medium text-muted-foreground">
        <span className={`rounded-full p-2 ${iconClassName}`}>{icon}</span>
        {label}
      </div>
      <div className="flex items-center gap-2 text-[1.45rem] font-black tracking-[-0.05em] text-foreground">
        {valueIcon ? <span className="text-[color:var(--primary)]">{valueIcon}</span> : null}
        {value}
      </div>
      <div className="mt-1 text-sm leading-6 text-muted-foreground">{supporting}</div>
    </div>
  )
}
