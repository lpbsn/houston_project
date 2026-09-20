import { AlertCircle, LoaderCircle, ShieldAlert } from 'lucide-react'
import type { ReactNode } from 'react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { OnboardingApiError } from '@/features/onboarding/api'
import type { ActivationBlocker } from '@/features/onboarding/types'

type OnboardingNoticeProps = {
  actions?: ReactNode
  message: string
  title: string
  tone?: 'default' | 'danger' | 'muted'
}

export function getOnboardingErrorMessage(error: unknown, fallback: string) {
  if (error instanceof OnboardingApiError) {
    return error.detail
  }

  if (error instanceof Error && error.message) {
    return error.message
  }

  return fallback
}

export function getOnboardingErrorStatus(error: unknown) {
  return error instanceof OnboardingApiError ? error.status : null
}

export function getOnboardingErrorBlockers(error: unknown) {
  return error instanceof OnboardingApiError ? error.blockers : []
}

export function OnboardingLoadingState({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-border bg-background px-4 py-4 text-sm text-muted-foreground">
      <LoaderCircle className="size-4 animate-spin text-primary" />
      {label}
    </div>
  )
}

export function OnboardingNotice({
  actions,
  message,
  title,
  tone = 'default',
}: OnboardingNoticeProps) {
  const iconClassName =
    tone === 'danger'
      ? 'bg-[#fff3f2] text-[#9d3b33]'
      : tone === 'muted'
        ? 'bg-[#fbf7f0] text-muted-foreground'
        : 'bg-[color:var(--primary)]/10 text-[color:var(--primary)]'

  return (
    <Card className="rounded-xl border-border bg-background shadow-none">
      <CardHeader className="gap-3">
        <span className={`w-fit rounded-full p-2 ${iconClassName}`}>
          {tone === 'danger' ? <ShieldAlert className="size-4" /> : <AlertCircle className="size-4" />}
        </span>
        <div className="space-y-2">
          <CardTitle className="text-lg font-semibold tracking-tight">
            {title}
          </CardTitle>
          <CardDescription className="text-sm leading-6">{message}</CardDescription>
        </div>
      </CardHeader>

      {actions ? <CardContent>{actions}</CardContent> : null}
    </Card>
  )
}

export function OnboardingErrorState({
  error,
  fallback,
}: {
  error: unknown
  fallback: string
}) {
  const status = getOnboardingErrorStatus(error)
  const blockers = getOnboardingErrorBlockers(error)
  const title =
    status === 403
      ? 'Ce compte ne peut pas accéder à cet onboarding.'
      : status === 404
        ? 'Cette session d’onboarding est indisponible.'
        : 'Impossible de charger l’onboarding.'

  return (
    <OnboardingNotice
      tone="danger"
      title={title}
      message={getOnboardingErrorMessage(error, fallback)}
      actions={blockers.length > 0 ? <BlockerList blockers={blockers} /> : null}
    />
  )
}

export function BlockerList({ blockers }: { blockers: ActivationBlocker[] }) {
  if (blockers.length === 0) {
    return (
      <div className="rounded-[1.15rem] border border-[#ebe2d5] bg-[#fbf7f0] px-4 py-3 text-sm text-muted-foreground">
        Aucun blocage renvoyé par le serveur.
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {blockers.map((blocker) => (
        <div
          key={`${blocker.code}-${blocker.message}`}
          className="rounded-[1.15rem] border border-[#f4d5d5] bg-[#fff8f6] px-4 py-3"
        >
          <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
            <div className="text-sm leading-6 text-[#87352f]">{blocker.message}</div>
            <Badge variant="outline" className="w-fit border-[#efc4c4] bg-white text-[#87352f]">
              {blocker.code}
            </Badge>
          </div>
        </div>
      ))}
    </div>
  )
}

export function RetryButton({ onClick }: { onClick: () => void }) {
  return (
    <Button
      type="button"
      variant="outline"
      className="h-10 w-full rounded-lg sm:w-auto"
      onClick={onClick}
    >
      Réessayer
    </Button>
  )
}
